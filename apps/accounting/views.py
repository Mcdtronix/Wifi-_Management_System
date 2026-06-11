"""
apps/accounting/views.py
-------------------------
RADIUS accounting ingestion and session reporting.

Two conceptual surfaces:
  1. RADIUS-facing: POST /api/accounting/radius/ — receives packets from FreeRADIUS
  2. Admin-facing:  GET  /api/accounting/sessions/ — browsable session history
"""

from django.db import transaction
from django.utils import timezone
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import RadiusAccounting, Session
from .serializers import (
    RadiusAccountingListSerializer,
    RadiusAccountingDetailSerializer,
    SessionListSerializer,
    SessionDetailSerializer,
    SessionFilterSerializer,
)


# ---------------------------------------------------------------------------
# RADIUS Accounting Receiver
# ---------------------------------------------------------------------------

class RadiusAccountingReceiver(APIView):
    """
    POST /api/accounting/radius/
    Receives Accounting-Start, Accounting-Update, and Accounting-Stop
    packets from FreeRADIUS via the rlm_rest module.

    Authentication: shared secret header (X-RADIUS-Secret) checked against
    settings.RADIUS_ACCOUNTING_SECRET.
    Not protected by JWT — RADIUS is internal network only.
    """

    permission_classes = [AllowAny]  # Protected by shared secret + network ACL

    def post(self, request, *args, **kwargs):
        # Verify shared secret
        from django.conf import settings
        secret = request.headers.get("X-Radius-Secret", "")
        if secret != getattr(settings, "RADIUS_ACCOUNTING_SECRET", ""):
            return Response(
                {"detail": "Unauthorized."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        acct_type = request.data.get("Acct-Status-Type", "")
        username = request.data.get("User-Name", "").strip()
        acct_unique_id = request.data.get("Acct-Unique-Session-Id", "").strip()

        if not acct_unique_id or not username:
            return Response(
                {"detail": "Acct-Unique-Session-Id and User-Name are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve subscriber
        from apps.subscribers.models import Subscriber
        subscriber = Subscriber.objects.filter(username=username, is_deleted=False).first()

        payload = self._map_radius_fields(request.data, subscriber)

        if acct_type == "Start":
            return self._handle_start(payload, subscriber)
        elif acct_type in ("Alive", "Interim-Update"):
            return self._handle_update(payload, acct_unique_id, subscriber)
        elif acct_type == "Stop":
            return self._handle_stop(payload, acct_unique_id, subscriber)
        else:
            return Response(
                {"detail": f"Unknown Acct-Status-Type: {acct_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    def _handle_start(self, payload: dict, subscriber) -> Response:
        record = RadiusAccounting.objects.create(**payload)
        if subscriber:
            Session.objects.create(
                subscriber=subscriber,
                radius_record=record,
                mac_address=payload.get("callingstationid", ""),
                client_ip=payload.get("framedipaddress"),
                state=Session.SessionState.ACTIVE,
                started_at=timezone.now(),
            )
        return Response({"detail": "Start recorded."}, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def _handle_update(self, payload: dict, unique_id: str, subscriber) -> Response:
        # Update the existing accounting record
        RadiusAccounting.objects.filter(acctuniqueid=unique_id).update(
            acctinputoctets=payload.get("acctinputoctets", 0),
            acctoutputoctets=payload.get("acctoutputoctets", 0),
            acctsessiontime=payload.get("acctsessiontime", 0),
        )
        # Update quota usage
        if subscriber:
            delta = payload.get("acctinputoctets", 0) + payload.get("acctoutputoctets", 0)
            self._update_quota(subscriber, delta)

        return Response({"detail": "Update recorded."}, status=status.HTTP_200_OK)

    @transaction.atomic
    def _handle_stop(self, payload: dict, unique_id: str, subscriber) -> Response:
        now = timezone.now()
        RadiusAccounting.objects.filter(acctuniqueid=unique_id).update(
            acctstoptime=now,
            acctinputoctets=payload.get("acctinputoctets", 0),
            acctoutputoctets=payload.get("acctoutputoctets", 0),
            acctsessiontime=payload.get("acctsessiontime", 0),
            acctterminatecause=payload.get("acctterminatecause", ""),
            acctstatustype=RadiusAccounting.AcctStatusType.STOP,
        )
        # Close session
        Session.objects.filter(
            radius_record__acctuniqueid=unique_id,
            state=Session.SessionState.ACTIVE,
        ).update(
            state=Session.SessionState.CLOSED,
            ended_at=now,
            upload_bytes=payload.get("acctinputoctets", 0),
            download_bytes=payload.get("acctoutputoctets", 0),
            duration_seconds=payload.get("acctsessiontime", 0),
            terminate_cause=payload.get("acctterminatecause", ""),
        )
        if subscriber:
            delta = payload.get("acctinputoctets", 0) + payload.get("acctoutputoctets", 0)
            self._update_quota(subscriber, delta)

        return Response({"detail": "Stop recorded."}, status=status.HTTP_200_OK)

    @staticmethod
    def _update_quota(subscriber, bytes_delta: int) -> None:
        """Update today's quota usage and suspend if threshold reached."""
        from django.utils import timezone
        from apps.quota.models import DailyQuotaUsage

        today = timezone.localdate()
        usage, _ = DailyQuotaUsage.objects.get_or_create(
            subscriber=subscriber,
            date=today,
            defaults={"bytes_used": 0},
        )
        quota_exceeded = usage.add_usage(bytes_delta)
        if quota_exceeded:
            from apps.notifications.tasks import send_notification_async
            send_notification_async.delay(
                event_type="quota_exceeded",
                subscriber_id=str(subscriber.id),
            )

    @staticmethod
    def _map_radius_fields(data: dict, subscriber) -> dict:
        """Map RADIUS attribute names to model field names."""
        return {
            "acctuniqueid": data.get("Acct-Unique-Session-Id", ""),
            "username": data.get("User-Name", ""),
            "realm": data.get("Realm", ""),
            "nasipaddress": data.get("NAS-IP-Address", "0.0.0.0"),
            "nasportid": data.get("NAS-Port-Id", ""),
            "nasporttype": data.get("NAS-Port-Type", ""),
            "acctstarttime": timezone.now(),
            "acctsessiontime": int(data.get("Acct-Session-Time", 0)),
            "acctauthentic": data.get("Acct-Authentic", ""),
            "acctstatustype": data.get("Acct-Status-Type", "Start"),
            "acctinputoctets": int(data.get("Acct-Input-Octets", 0)),
            "acctoutputoctets": int(data.get("Acct-Output-Octets", 0)),
            "calledstationid": data.get("Called-Station-Id", ""),
            "callingstationid": data.get("Calling-Station-Id", ""),
            "framedipaddress": data.get("Framed-IP-Address") or None,
            "acctterminatecause": data.get("Acct-Terminate-Cause", ""),
            "servicetype": data.get("Service-Type", ""),
            "subscriber": subscriber,
        }


# ---------------------------------------------------------------------------
# Admin Session Browser
# ---------------------------------------------------------------------------

class RadiusAccountingViewSet(ReadOnlyModelViewSet):
    """
    GET  /api/accounting/records/
    GET  /api/accounting/records/{id}/
    Read-only admin access to raw RADIUS accounting records.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["acctstarttime", "acctstoptime", "username"]
    ordering = ["-acctstarttime"]

    def get_queryset(self):
        qs = RadiusAccounting.objects.select_related("subscriber")
        username = self.request.query_params.get("username")
        acct_type = self.request.query_params.get("type")
        if username:
            qs = qs.filter(username__icontains=username)
        if acct_type:
            qs = qs.filter(acctstatustype=acct_type)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return RadiusAccountingListSerializer
        return RadiusAccountingDetailSerializer


class SessionViewSet(ReadOnlyModelViewSet):
    """
    GET  /api/accounting/sessions/
    GET  /api/accounting/sessions/{id}/
    active: GET /api/accounting/sessions/active/
    summary: GET /api/accounting/sessions/summary/?subscriber_id=<uuid>
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["started_at", "ended_at", "duration_seconds"]
    ordering = ["-started_at"]

    def get_queryset(self):
        qs = Session.objects.select_related("subscriber", "radius_record").filter(
            is_deleted=False
        )
        subscriber_id = self.request.query_params.get("subscriber_id")
        session_state = self.request.query_params.get("state")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if subscriber_id:
            qs = qs.filter(subscriber_id=subscriber_id)
        if session_state:
            qs = qs.filter(state=session_state)
        if start_date:
            qs = qs.filter(started_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(started_at__date__lte=end_date)

        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return SessionListSerializer
        return SessionDetailSerializer

    @action(detail=False, methods=["get"], url_path="active")
    def active(self, request):
        """GET /api/accounting/sessions/active/ — all sessions currently online."""
        qs = self.get_queryset().filter(state=Session.SessionState.ACTIVE)
        return Response(SessionListSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        GET /api/accounting/sessions/summary/?subscriber_id=<uuid>
        Returns aggregate usage stats for a subscriber.
        """
        from django.db.models import Sum, Count, Avg

        subscriber_id = request.query_params.get("subscriber_id")
        if not subscriber_id:
            return Response(
                {"detail": "subscriber_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = self.get_queryset().filter(
            subscriber_id=subscriber_id,
            state=Session.SessionState.CLOSED,
        )
        agg = qs.aggregate(
            total_sessions=Count("id"),
            total_upload_bytes=Sum("upload_bytes"),
            total_download_bytes=Sum("download_bytes"),
            total_duration_seconds=Sum("duration_seconds"),
            avg_session_seconds=Avg("duration_seconds"),
        )
        return Response(agg)