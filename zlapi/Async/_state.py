# -*- coding: UTF-8 -*-
import attr
import random
import asyncio
import aiohttp

from .. import _util, _exception


class State(object):
	def __init__(cls):
		cls._config = {}
		cls._headers = _util.HEADERS
		cls._cookies = _util.COOKIES
		cls.user_id = None
		cls.user_imei = None
		cls._loggedin = False

	def is_logged_in(cls):
		return cls._loggedin

	def set_cookies(cls, cookies):
		cls._cookies = cookies

	def set_secret_key(cls, secret_key):
		cls._config["secret_key"] = secret_key

	async def get_cookies(cls):
		return cls._cookies

	async def get_secret_key(cls):
		return cls._config.get("secret_key")

	async def _get(cls, *args, **kwargs):
		async with aiohttp.ClientSession() as session:
			async with session.get(*args, **kwargs, headers=cls._headers, cookies=cls._cookies) as response:
				try:
					return await response.json(content_type=None)
				except Exception:
					# Fallback to text if response isn't JSON
					return await response.text()

	async def _post(cls, *args, **kwargs):
		async with aiohttp.ClientSession() as session:
			async with session.post(*args, **kwargs, headers=cls._headers, cookies=cls._cookies) as response:
				try:
					return await response.json(content_type=None)
				except Exception:
					return await response.text()

	async def login(cls, phone, password, imei, session_cookies=None, user_agent=None):
		"""Attempt to initialise session using existing cookies.

		This implementation calls Zalo's own login info endpoint instead of
		relying on third-party services.
		"""
		if cls._cookies and cls._config.get("secret_key"):
			cls._loggedin = True
			return

		if user_agent:
			cls._headers["User-Agent"] = user_agent

		if cls._cookies:
			params = {
				"imei": imei,
				"type": 30,
				"client_version": 645,
				"computer_name": "Web",
				"ts": _util.now(),
			}
			try:
				# Call Zalo's getLoginInfo endpoint directly
				url = f"https://wpa.chat.zalo.me/api/login/getLoginInfo"
				data = await cls._get(url, params=params)

				# Response format mirrors the synchronous State.login implementation
				if isinstance(data, dict) and data.get("data"):
					zpw = data["data"].get("zpw_ws")
					uid = data["data"].get("uid")
					phone_num = data["data"].get("phone_number")
					key = data["data"].get("zpw_enk")

					content = {
						"data": {
							"phone_number": str(phone_num),
							"secret_key": str(key),
							"send2me_id": str(uid),
							"zpw_ws": zpw,
						},
						"error_code": 0,
					}

					if content.get("error_code") == 0:
						cls._config = content.get("data")

						if cls._config.get("secret_key"):
							cls._loggedin = True
							cls.user_id = cls._config.get("send2me_id")
							cls.user_imei = imei
						else:
							cls._loggedin = False
							raise _exception.ZaloLoginError("Unable to get `secret key`.")
					else:
						error = data.get("error_code")
						content_msg = data.get("error_message")
						raise _exception.ZaloLoginError(f"Error #{error} when logging in: {content_msg}")
				else:
					raise _exception.ZaloLoginError("Invalid response when logging in")

			except _exception.ZaloLoginError as e:
				raise _exception.ZaloLoginError(str(e))
			except Exception as e:
				raise _exception.ZaloLoginError(f"An error occurred while logging in! {str(e)}")
		else:
			raise _exception.LoginMethodNotSupport("Login method is not supported yet")

	def start_auto_renew(cls, interval: int = 300):
		"""Start a background task that periodically refreshes the session.

		This is a best-effort refresh: it re-calls the login endpoint and
		updates `secret_key` when cookies exist. Call this from an asyncio
		loop (e.g. `asyncio.get_event_loop().create_task(... )`).
		"""
		try:
			loop = asyncio.get_event_loop()
		except RuntimeError:
			# No running loop
			return None

		async def _auto():
			while True:
				try:
					if cls._cookies:
						await cls.login(None, None, cls.user_imei or "", None)
				except Exception:
					# swallow errors; we'll retry on next interval
					pass
				await asyncio.sleep(interval)

		return loop.create_task(_auto())
	

