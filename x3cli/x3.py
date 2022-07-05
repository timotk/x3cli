import logging
import functools
import getpass
import json
import pickle
import warnings
from pathlib import Path
from typing import Dict

from appdirs import user_data_dir
from requests_html import HTMLSession

logger = logging.getLogger(__name__)
save_dir = Path(user_data_dir(appname="x3cli"))
save_dir.mkdir(exist_ok=True)
CACHE = Path(save_dir) / "cache.pkl"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS; rv:94.0) Gecko/20100101 Firefox/94.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://x3.nodum.io/grid",
    "DNT": "1",
    "Connection": "keep-alive",
}


def login_required(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not all([self.employee_id, self.secure, "NODUMXEBIAURENBOEKEN3" in self.session.cookies]):
            self.set_from_cache()
        if self.is_authenticated():
            logger.debug("You are already logged in")
        else:
            logger.debug("Removing cache")
            CACHE.unlink(missing_ok=True)
            hint = f" ({self.username})" if self.username else ""
            username_input = input(f"Username{hint}: ")
            if username_input:
                self.username = username_input
            password = getpass.getpass()
            logger.debug(f"Logging you in as {self.username}")
            self.login(username=self.username, password=password)
        result = func(self, *args, **kwargs)
        return result
    return wrapper


class X3:
    def __init__(self):
        self.session = HTMLSession()
        self.session.headers.update(DEFAULT_HEADERS)
        self.employee_id = None
        self.username = None
        self.name = None
        self.secure = None
        self._is_authenticated = False
        self.set_from_cache()

    def is_authenticated(self):
        if not self._is_authenticated:
            url = "https://37432.afasinsite.nl/x3/timemanagement"
            response = self.session.get(url)
            if any([
                response.url.startswith(f"https://{prefix}")
                for prefix
                in ["sts.afasonline.com", "idp.afasonline.com"]
            ]):  # We are redirected to the login page, so we are logged in
                logger.debug("Can't get data, not logged in")
                self._is_authenticated = False
            else:
                logger.debug("You can login!")
                self._is_authenticated = True
        return self._is_authenticated

    def set_from_cache(self):
        if CACHE.exists():
            with open(CACHE, "rb") as f:
                cache = pickle.load(f)
                logger.debug(f"Setting attributes {cache.keys()} from cache")
                for attr, value in cache.items():
                    # if "." in attr:  # for setting session.cookies
                    #     attr, subattr = attr.split(".")
                    #     setattr(getattr(self, attr), subattr, value)
                    # else:
                    setattr(self, attr, value)
        else:
            warnings.warn("Cache not found")

    def save_to_cache(self, cache: Dict):
        with open(CACHE, "wb") as f:
            pickle.dump(cache, f)

    def login(self, username: str, password: str):
        # Insite will redirect us via javascript
        insite_response = self.session.get("https://37432.afasinsite.nl/x3/timemanagement")
        insite_response.raise_for_status()

        if not insite_response.url.startswith("https://idp.afasonline.com"):
            raise ValueError(f"Insite did not redirect to idp.afasonline.com. Actual url: {insite_response.url}")

        # Grab csrf_token from javascript
        csrf_token = insite_response.html.find("script")[0].text.split('"')[1]

        data = {
            "Username": username,
            "Token": "",
            "Captcha": "False",
            "Password": password,
            "ReturnUrl": "",
            "__RequestVerificationToken": csrf_token,
        }

        # First, login
        login_response = self.session.post(
            'https://idp.afasonline.com/Account/Password',
            data=data,
        )
        login_response.raise_for_status()

        # Errors can occur when password is wrong or you are sending too many 2FA requests
        errors = login_response.html.find("div .validation-summary-errors li")
        if errors:
            raise Exception(
                    f"{len(errors)} error encountered during login: "
                    f"{','.join([error.text for error in errors])}"
            )

        # Sometimes, you will be asked for your 2FA code
        if login_response.url.startswith("https://idp.afasonline.com/TwoFactor/Confirm"):
            authentication_code = input("Input your 2FA code: ")

            data = {
                "Method": "GenericTotp",
                "TwoFactorKey": "",
                "Code": authentication_code,
                "__RequestVerificationToken": csrf_token,
                # UI has a checkbox: Trust Device for 7 days.
                "TrustedDevice": True,
            }
            two_factor_response = self.session.post(login_response.url, data=data)
            two_factor_response.raise_for_status()
            if not two_factor_response.url.startswith("https://x3.nodum.io"):
                raise ValueError(f"Did not redirect to x3.nodum.io. Actual url {two_factor_response.url}, did you enter the correct 2FA code?")

            # Our headers need to pass the X3 cookie
            # We get the cookie by doing a requests to X3 first, then updating the header
            # response = self.session.get('https://x3.nodum.io/grid')
            x3_cookie = self.session.cookies["NODUMXEBIAURENBOEKEN3"]
            self.session.headers.update(
                {"Cookie": f"NODUMXEBIAURENBOEKEN3={x3_cookie}"}
            )

            def parse_js_employee_object(text):
                obj_str = text.split("{ ")[-1].split(" }")[0]

                employee_obj = {}
                for line in obj_str.split(","):
                    key, value = line.split(":")
                    key = key.strip()
                    value = value.replace("'", "").replace('"', "").strip()
                    employee_obj[key] = value

                return employee_obj

            # Some of your data is saved in a javascript object inside the X3 html
            response = self.session.get("https://x3.nodum.io/grid")
            response.raise_for_status()
            script_text = response.html.find("script")[-3].text
            employee = parse_js_employee_object(script_text)
            self.secure = employee['secure']
            self.employee_id = employee['id']

        logger.debug("You should be logged in!")

        # TODO: Validate this
        cache = {
            "employee_id": self.employee_id,
            "secure": self.secure,
            "session": self.session,
            "username": self.username,
        }
        self.save_to_cache(cache)

    @login_required
    def geldig(self, year: int, month: int):
        params = {
            "employee": self.employee_id,
            "secure": self.secure,
            "y": year,
            "m": month,
        }

        response = self.session.post("https://x3.nodum.io/json/geldig", params=params)
        logger.debug(response, response.url)
        response.raise_for_status()
        if response.json() is None:
            raise ValueError("json response is None")
        if response.text == "":
            raise ValueError("Response is empty")
        if len(response.json()['projects']) == 1:
            raise ValueError("Only one project found, you are not logged in")
        return response.json()

    @login_required
    def illness(self, month: int, year: int):
        params = {
            "employee": self.employee_id,
            "secure": self.secure,
            "y": year,
            "m": month,
        }

        response = self.session.post("https://x3.nodum.io/json/illness", params=params)
        response.raise_for_status()
        if response.json() is None:
            raise ValueError("json response is None")
        if response.text == "":
            raise ValueError("Response is empty")
        return response.json()

    @login_required
    def lines(self, year: int, month: int):
        data = {
            "moment": {"month": str(month), "year": str(year)},
            "user": {
                "name": self.name,
                "id": str(self.employee_id),
                "secure": self.secure,
                "see": "false",
            },
        }
        response = self.session.post(
            "https://x3.nodum.io/json/fetchlines",
            files=dict(json=(None, json.dumps(data))),
        )
        response.raise_for_status()

        if response.json() is None:
            raise ValueError("json response is None")
        if response.text == "":
            raise ValueError("Response is empty")

        return response.json()
