"""Simulated internal DMS boundary. No Tekion API or private schema compatibility."""

from ..store import get, all_records


class LocalDMSAdapter:
    def __init__(self, session, dealer):
        self.session = session
        self.dealer = dealer

    def vehicle(self, id):
        return get(self.session, "vehicle", id, self.dealer)

    def vehicles(self):
        return all_records(self.session, "vehicle", self.dealer)

    def service_visit(self, id):
        return get(self.session, "visit", id, self.dealer)

    def events(self, vehicle_id):
        return [
            r for r in all_records(self.session, "event", self.dealer) if r["vehicle"] == vehicle_id
        ]
