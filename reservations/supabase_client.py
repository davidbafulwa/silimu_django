from django.conf import settings

_supabase_client = None


def get_client():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        return None
    from supabase import create_client
    _supabase_client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
    )
    return _supabase_client


def get_service_client():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return None
    from supabase import create_client
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )


# --------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------

def sign_up(email, password, user_data=None):
    client = get_client()
    if not client:
        return None, "Supabase non configuré"
    try:
        response = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": user_data or {}},
        })
        return response, None
    except Exception as exc:
        return None, str(exc)


def sign_in(email, password):
    client = get_client()
    if not client:
        return None, "Supabase non configuré"
    try:
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        return response, None
    except Exception as exc:
        return None, str(exc)


def sign_out(access_token=None):
    client = get_client()
    if not client:
        return False
    try:
        if access_token:
            client.auth.admin_sign_out(access_token)
        else:
            client.auth.sign_out()
        return True
    except Exception:
        return False


def get_user(access_token):
    client = get_client()
    if not client:
        return None
    try:
        response = client.auth.get_user(access_token)
        return response.user if response else None
    except Exception:
        return None


def get_user_by_id(user_id):
    client = get_service_client()
    if not client:
        return None
    try:
        response = client.auth.admin.get_user_by_id(user_id)
        return response.user if response else None
    except Exception:
        return None


def create_user(email, password, user_data=None):
    client = get_service_client()
    if not client:
        return None, "Supabase non configuré"
    try:
        response = client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": user_data or {},
        })
        return response, None
    except Exception as exc:
        return None, str(exc)


def delete_user(user_id):
    client = get_service_client()
    if not client:
        return False
    try:
        client.auth.admin.delete_user(user_id)
        return True
    except Exception:
        return False


def send_magic_link(email):
    client = get_client()
    if not client:
        return None, "Supabase non configuré"
    try:
        response = client.auth.sign_in_with_otp({
            "email": email,
            "options": {"should_create_user": True},
        })
        return response, None
    except Exception as exc:
        return None, str(exc)


# --------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------

def upload_file(bucket, path, file_data, content_type=None):
    client = get_service_client()
    if not client:
        return None, "Supabase non configuré"
    try:
        kwargs = {"file_options": {"content_type": content_type}} if content_type else {}
        response = client.storage.from_(bucket).upload(
            path, file_data, **kwargs
        )
        return response, None
    except Exception as exc:
        return None, str(exc)


def download_file(bucket, path):
    client = get_service_client()
    if not client:
        return None, "Supabase non configuré"
    try:
        response = client.storage.from_(bucket).download(path)
        return response, None
    except Exception as exc:
        return None, str(exc)


def get_public_url(bucket, path):
    client = get_client()
    if not client:
        return None
    try:
        return client.storage.from_(bucket).get_public_url(path)
    except Exception:
        return None


def get_signed_url(bucket, path, expiry_seconds=None):
    client = get_service_client()
    if not client:
        return None, "Supabase non configuré"
    expiry = expiry_seconds or settings.SUPABASE_STORAGE_EXPIRY
    try:
        response = client.storage.from_(bucket).create_signed_url(
            path, expiry
        )
        return response.get("signedURL") if response else None, None
    except Exception as exc:
        return None, str(exc)


def list_files(bucket, folder=None):
    client = get_service_client()
    if not client:
        return [], "Supabase non configuré"
    try:
        path = folder or ""
        response = client.storage.from_(bucket).list(path)
        return response, None
    except Exception as exc:
        return [], str(exc)


def delete_file(bucket, path):
    client = get_service_client()
    if not client:
        return False, "Supabase non configuré"
    try:
        client.storage.from_(bucket).remove([path])
        return True, None
    except Exception as exc:
        return False, str(exc)


def ensure_bucket(bucket_name, public=False):
    client = get_service_client()
    if not client:
        return False, "Supabase non configuré"
    try:
        buckets = client.storage.list_buckets()
        if not any(b.name == bucket_name for b in buckets):
            client.storage.create_bucket(bucket_name, options={"public": public})
        return True, None
    except Exception as exc:
        return False, str(exc)


# --------------------------------------------------------------------
# Real-time
# --------------------------------------------------------------------

def get_realtime_client():
    client = get_client()
    if not client:
        return None
    try:
        return client.realtime
    except Exception:
        return None


def subscribe_to_channel(channel, event, callback):
    realtime = get_realtime_client()
    if not realtime:
        return None, "Supabase non configuré"
    try:
        sub = realtime.channel(channel).on(event, callback).subscribe()
        return sub, None
    except Exception as exc:
        return None, str(exc)
