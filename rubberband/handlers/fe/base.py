"""Common class to derive all rubberband request handlers from."""
from collections import Iterable
from datetime import datetime
from tornado.web import RequestHandler
from tornado.options import options
import traceback

from rubberband.constants import NONE_DISPLAY, INFINITY_KEYS, \
        INFINITY_MASK, INFINITY, INFINITY_DISPLAY, FORMAT_DATETIME_SHORT


class BaseHandler(RequestHandler):
    """Custom overrides."""

    def get_rb_url(self):
        """
        Url where the rubberband instance lives.

        Returns
        -------
        str
            the rubberband url
        """
        return self.request.protocol + "://" + self.request.host + self.request.uri

    def get_current_user(self):
        """
        Get the name of the User that sent the request.

        Returns
        -------
        str
            Current user
        """
        if not self.settings["debug"]:
            # self.request is single HTTP requestobject of type 'tornado.httputil.HTTPServerRequest'
            headers = dict(self.request.headers.get_all())
            return headers.get("X-Forwarded-Email")
        else:
            return "debug"

    def get_cookie(self, name="_oauth2_proxy"):
        """
        Get the cookie from the request.

        Parameters
        ----------
        name : str
            The name of the cookie

        Returns
        -------
        str
            The value of the cookie.
        """
        if not self.settings["debug"]:
            cookie_val = self.request.cookies.get(name).value
            return cookie_val
        else:
            return None

    def write_error(self, status_code, msg="", **kwargs):
        """
        Send an error page back to the user.

        Parameters
        ----------
        status_code : int
            The status code of the error to be written.
        msg : str
            The message to be printed (default "").
        kwargs : keyword arguments
            keyword arguments for `traceback.format_exception`
        """
        if status_code == 400:
            self.render("400.html", msg=msg)
            return
        if status_code == 404:
            #  'Simply render the template to a string and pass it to self.write'
            self.render("404.html")
            return
        else:
            msg = "\n".join(traceback.format_exception(*kwargs["exc_info"]))
            self.render("500.html", msg=msg)
            return

    def get_template_namespace(self):
        """Return a dictionary to be used as the default template namespace.

        May be overridden by subclasses to add or modify values.

        The results of this method will be combined with additional
        defaults in the `tornado.template` module and keyword arguments
        to `render` or `render_string`.
        """
        namespace = dict(
            handler=self,
            request=self.request,
            current_user=self.current_user,
            locale=self.locale,
            _=self.locale.translate,
            pgettext=self.locale.pgettext,
            static_url=self.static_url,
            xsrf_form_html=self.xsrf_form_html,
            reverse_url=self.reverse_url,
            format_attr=self.format_attr,
            format_type=self.format_type,
            format_attrs=self.format_attrs,
            get_objsen=self.get_objsen,
            are_equivalent=self.are_equivalent,
            options=options,
        )

        # additional ui modules
        namespace.update(self.ui)

        return namespace

    def format_type(self, obj, attr):
        """
        Return type of attribute of obj.

        Parameters
        ----------
        obj : object
        attr : attribute of obj

        Returns
        -------
        str
            type of attr of obj or ""
        """
        if attr in ["instance_type", "OriginalProblem_InitialNCons"]:
            return "text"
        if attr in ["OriginalProblem_Vars", "PresolvedProblem_InitialNCons", "PresolvedProblem_Vars", "DualBound", "PrimalBound", "Gap", "Iterations", "Nodes", "TotalTime_solving"]:
            return "number"
        value = getattr(obj, attr, None)
        if isinstance(value, str):
            return "text"
        if isinstance(value, float) or isinstance(value, int):
            return "number"
        return ""

    def format_attr(self, obj, attr):
        """
        Format values (attributes attr of obj).

        Value gets properly formatted if attr is a single attribute.
        If attr is a list, the keys are concatenated with " ".

        Parameters
        ----------
        obj : object
        attr: key or list of keys of obj

        Returns
        -------
        str
            type of attr of obj
        """
        if isinstance(attr, list):
            value = []
            for i in attr:
                v = getattr(obj, i, None)
                if v is not None and v != "":
                    value.append(v)
            if value == []:
                return NONE_DISPLAY
            return " ".join(value)
        else:
            value = getattr(obj, attr, None)
            if value not in (None, ""):
                if attr in INFINITY_KEYS and value == INFINITY_MASK:
                    return INFINITY_DISPLAY
                if (type(value) is int or type(value) is float):
                    if value >= INFINITY:
                        return INFINITY_DISPLAY
                    if value <= -INFINITY:
                        return -INFINITY_DISPLAY
                if attr in ["DualBound", "PrimalBound"]:
                    return "%.4f" % value
                if attr in ["SolvingTime", "TotalTime_solving", "Gap"]:
                    return "%.2f" % value
                if attr in ["Iterations"]:
                    return int(value)
                if attr.endswith("_timestamp") or attr.endswith("expirationdate"):
                    return datetime.strftime(value, FORMAT_DATETIME_SHORT)
                if isinstance(value, str):
                    return value
                if isinstance(value, Iterable):
                    return ", ".join([str(v) for v in value])
                return value
            return NONE_DISPLAY

    def get_objsen(self, objs, inst_name):
        """
        Return the objective sense based on the fields Objsense, PrimalBound, DualBound.

        Parameters
        ----------
        objs: set/list of TestSets
        inst_name: instance/problem name

        Returns
        -------
        int
            -1 if obj is a maximation problem (pb <= db), 1 if minimization (pb >= db), 0 else
        """
        objsen = None
        for o in objs:
            objsen = getattr(o.children[inst_name], "Objsense", None)
            if objsen is not None:
                return float(objsen)
        for o in objs:
            try:
                pb = float(getattr(o.children[inst_name], "PrimalBound", None))
                db = float(getattr(o.children[inst_name], "DualBound", None))
                if pb > db:
                    # minimize
                    return 1
                elif pb < db:
                    # maximize
                    return -1
            except:
                pass
        return 0

    def format_attrs(self, objs, attr, inst_name):
        """
        Return sorted attribute (attr) of an instance (inst_name) from multiple TestSets (objs) as a formatted string separated by newlines.

        Parameters
        ----------
        objs: set/list of TestSets
        attr: attribute
        inst_name: instance/problem name

        Returns
        -------
        str
            all atributes formatted
        """
        attr_str = []
        for o in objs:
            val = self.format_attr(o.children[inst_name], attr)
            attr_str.append(val)

        partial_list = sorted([a for a in attr_str
            if a is not None and type(a) in [int, float]], reverse=True)
        partial_list.extend(sorted([a for a in attr_str
            if a is not None and type(a) not in [int, float]], reverse=True))
        partial_list.extend([NONE_DISPLAY for a in attr_str if a is None])
        return "\n".join(map(str, partial_list))

    def are_equivalent(self, one, two, attr):
        """
        Decide if the data in attr is the same in both TestSets one and two.

        Parameters
        ----------
        one : TestSet
        two : TestSet
        attr : attributes of one and two

        Returns
        -------
        bool
            Decide if a i
        """
        a = self.format_attr(one, attr)
        b = self.format_attr(two, attr)
        return a == b
