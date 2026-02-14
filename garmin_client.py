from datetime import date, datetime, timedelta

from garminconnect import Garmin

TOKENSTORE = "~/.garminconnect"


class GarminClient:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.client = Garmin(email, password, return_on_mfa=True)
        self._client_state = None

    def login(self) -> bool:
        """Login to Garmin Connect. Returns True if MFA is needed."""
        try:
            self.client.login(tokenstore=TOKENSTORE)
            return False
        except Exception:
            self.client = Garmin(
                self.email, self.password, return_on_mfa=True
            )
            result = self.client.login()
            if result and result[0] == "needs_mfa":
                self._client_state = result[1]
                return True
            self.client.garth.dump(TOKENSTORE)
            return False

    def resume_mfa(self, mfa_code: str):
        """Complete login with MFA code."""
        self.client.resume_login(self._client_state, mfa_code)
        self.client.garth.dump(TOKENSTORE)

    def get_all_activities(self) -> list[dict]:
        activities = []
        start = 0
        limit = 100
        while True:
            batch = self.client.get_activities(start=start, limit=limit)
            if not batch:
                break
            activities.extend(batch)
            if len(batch) < limit:
                break
            start += limit
        return activities

    def get_activities_since(self, since: str) -> list[dict]:
        start_date = datetime.strptime(since, "%Y-%m-%d %H:%M:%S").date()
        end_date = date.today() + timedelta(days=1)
        return self.client.get_activities_by_date(
            startdate=start_date.isoformat(),
            enddate=end_date.isoformat(),
        )
