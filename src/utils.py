class Counter:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._total_subrequests_count = 0
        self._check_subrequest_count = 0
        self._debtor_subrequest_count = 0

    def increment_total_subrequest(self):
        self._total_subrequests_count += 1

    def increment_debtor_subrequest(self):
        self._debtor_subrequest_count += 1

    def increment_check_subrequest(self):
        self._check_subrequest_count += 1

    def get_total_subrequests(self):
        return self._total_subrequests_count

    def get_debtor_subrequests(self):
        return self._debtor_subrequest_count

    def get_check_subrequests(self):
        return self._check_subrequest_count


counter = Counter()
