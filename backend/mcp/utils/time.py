from datetime import timezone

def localize_tz(dt):
    return dt.astimezone(timezone.utc)
