"""Define data models and methods, also used by elasticsearch_dsl."""
import gzip
import json
import datetime
from elasticsearch_dsl import DocType, InnerDoc, Text, Keyword, Date, Float, Nested
from ipet import Key

from rubberband.constants import INFINITY_KEYS, INFINITY_MASK, ELASTICSEARCH_INDEX, INFINITY_FLOAT
from .model_helpers import compute_stat


class File(InnerDoc):
    """The definition of a File object. A `File` contains the raw contents of a log file."""

    type = Keyword(index=True, required=True)  # out, set, err, solu
    filename = Text(index=False, required=True)  # check.MMM.scip-021ace1...out
    hash = Keyword(index=True, required=True)  # computed hash
    testset_id = Keyword(index=True, required=True)  # for application-side joins
    text = Text(index=False, required=True)  # this field is not indexed and is not searchable

    class Meta:
        index = ELASTICSEARCH_INDEX
        # doc_type = "file"

    def __str__(self):
        """Return a string description of the file object."""
        return "File {} {}".format(self.filename, self.type)


class Result(InnerDoc):
    """
    The definition of a result object. A `Result` is the result of a single instance run.

    Attributes:
        instance_name
        instance_type
        SoluFileStatus
        Status
        Datetime_Start
        Datetime_End
        dualboundhistory
        PrimalBoundHistory
        ...

    Methods:
        raw
        json
        csv
        gzip
    """

    instance_name = Keyword(index=True, required=True)  # mcf128-4-1
    instance_id = Keyword(index=True, required=True)  # mcf128-4-1
    instance_type = Keyword(index=True)  # CIP
    SoluFileStatus = Keyword(index=True)
    Status = Keyword(index=True)
    Datetime_Start = Date()
    Datetime_End = Date()
    dualboundhistory = Float(multi=True)
    PrimalBoundHistory = Float(multi=True)

    class Meta:
        index = ELASTICSEARCH_INDEX
        # doc_type = "result"

    def __str__(self):
        """Return a string description of the result object."""
        return "Result {}".format(self.instance_name)

    def raw(self, ftype=".out"):
        """
        Return a log of Result object from logfile.

        Parameters
        ----------
        ftype : str
            extension of file to get data from (default ".out")
        """
        parent = TestSet.get(id=self.meta.parent)
        whole_file = parent.raw(ftype=".out")
        # TODO: remove this once integer/ipet#20 is resolved
        # this is a hack for optimization/rubberband#41
        if hasattr(self, "LineNumbers_BeginLogFile") and hasattr(self, "LineNumbers_EndLogFile"):
            parts = whole_file.splitlines()[int(self.LineNumbers_BeginLogFile):
                                            int(self.LineNumbers_EndLogFile)]
            return "\n".join(parts)
        else:
            return "Unable to locate instance in out file :("

    def json(self, ftype=".out"):
        """
        Return a data of Result object from logfile in JSON format.

        Parameters
        ----------
        ftype : str
            extension of file to get data from (default ".out")
        """
        return json.dumps(self.to_dict(), default=date_handler)

    def csv(self, ftype=".out"):
        """
        Return a data of Result object from logfile in CSV format.

        Parameters
        ----------
        ftype : str
            extension of file to get data from (default ".out")
        """
        raise NotImplemented()

    def gzip(self, ftype=".out"):
        """
        Return a gzipped log of Result object.

        Parameters
        ----------
        ftype : str
            extension of file to get data from (default ".out")
        """
        raise NotImplemented()


class TestSet(DocType):
    """Define TestSet object, derived from DocType."""

    id = Keyword(index=True, required=True)
    filename = Text(index=False, required=True)
    solver = Keyword(index=False, required=True)  # scip
    run_initiator = Keyword(index=True, required=True)  # Gregor Hendel, last editor
    tags = Keyword() # user-provided tags
    test_set = Keyword(index=True)  # 'MMM', 'short', 'miplib2010', 'bugs', 'SAP-MMP'
    solver_version = Keyword(index=True)  # 3.0.1.1
    run_environment = Keyword(index=True)
    os = Keyword(index=True)
    architecture = Keyword(index=True)
    mode = Keyword(index=True)
    opt_flag = Keyword(index=True)  # spx1, spx2, cpx
    time_limit = Keyword(index=True)
    lp_solver = Keyword(index=True)  # SoPlex
    lp_solver_version = Keyword(index=True)  # 1.7.0.2
    lp_solver_githash = Keyword(index=True)
    git_hash = Keyword(index=True)  # af21b01
    git_commit_author = Keyword(index=True)  # Gregor Hendel
    settings_short_name = Keyword(index=True)  # default
    index_timestamp = Date(required=True)
    git_commit_timestamp = Date()  # required for plotting
    upload_timestamp = Date()
    uploader = Keyword(index=True)
    settings = Nested(
            properties={
                "solvingphases/optimalvalue" : Text(index=False),
                "misc/referencevalue": Text(index=False),
                # find out what is up with inftyvalues
                #"separating/flowcover/maxslackroot" : Text(index=False),
                #"separating/flowcover/maxslack" : Text(index=False),
                #"heuristics/undercover/maxcoversizeconss" : Text(index=False),
                })
    settings_default = Nested(
            properties={
                "solvingphases/optimalvalue" : Text(index=False),
                "misc/referencevalue": Text(index=False),
                # find out what is up with inftyvalues
                #"separating/flowcover/maxslackroot" : Text(index=False),
                #"separating/flowcover/maxslack" : Text(index=False),
                #"heuristics/undercover/maxcoversizeconss" : Text(index=False),
                })
    seed = Keyword(index=True)
    permutation = Keyword(index=True)
    metadata = Nested()
    expirationdate = Date(required=False)
    results = Nested(Result)
    files = Nested(File)

    class Meta:
        index = ELASTICSEARCH_INDEX
        #doc_type = "testset"

    def add_result(self, **kwargs):
        self.results.append(
                Result(**kwargs))

    def add_file(self, **kwargs):
        self.files.append(
                File(**kwargs))

    def update(self, **kwargs):
        """
        Extend update method, to deal with infinities before saving in elasticsearch.

        Parameters
        ----------
        kwargs
            keyword arguments
        """
        self.mask_infinities(**kwargs)
        return super(TestSet, self).update(**kwargs)

    def save(self, **kwargs):
        """
        Extend save method, to deal with infinities before saving in elasticsearch.

        Parameters
        ----------
        kwargs
            keyword arguments
        """
        self.mask_infinities(**kwargs)
        return super(TestSet, self).save(**kwargs)

    def mask_infinities(self, **kwargs):
        """
        Substitute infinities in fields for elasticsearch to be able to deal with them.

        Cast infinity to INFINITY_MASK, since databases don't like infinity.
        This is likely ok, because fields that could contain infinity, are [0, inf)
        and mask is -1.

        Parameters
        ----------
        kwargs
            keyword arguments
        """
        for i in INFINITY_KEYS:
            if getattr(self.settings, i, None) == INFINITY_FLOAT:
                setattr(self.settings, i, INFINITY_MASK)
            if getattr(self.settings_default, i, None) == INFINITY_FLOAT:
                setattr(self.settings_default, i, INFINITY_MASK)
            if kwargs != {} and "settings" in kwargs.keys() and i in kwargs["settings"].keys():
                if kwargs["settings"][i] == INFINITY_FLOAT:
                    kwargs["settings"][i] = INFINITY_MASK
                if kwargs["settings_default"][i] == INFINITY_FLOAT:
                    kwargs["settings_default"][i] = INFINITY_MASK

    def __str__(self):
        """Return a string description of the testset object."""
        return "TestSet {}".format(self.filename)

    @property
    def get_uploader(self):
        """Return original uploader TestSet object."""
        if self.uploader is not None:
            return self.uploader
        else:
            return self.run_initiator

    def get_filename(self, ending=".out"):
        """
        Return filename of file associated to TestSet object.

        Parameters
        ----------
        ending : str
            extension of file to get data from (default ".out")
        """
        if not ending or ending == ".out":
            return self.filename
        else:
            return self.filename.rsplit(".", 1)[0] + ending

    def raw(self, ftype=".out"):
        """
        Return raw content of file assiociated to TestSet object.

        Parameters
        ----------
        ftype : str
            extension of file to get data from (default ".out")
        """
        s = File.search()
        s = s.filter("term", testset_id=self.meta.id)
        s = s.filter("term", type=ftype.lstrip("."))
        try:
            contents = s.execute()[0].text
        except:
            contents = None

        return contents

    def gzip(self, ftype=".out"):
        """
        Return the data contained in the TestSet object in Gzip format.

        Parameters
        ----------
        ftype : str
            extension of file to get data from (default ".out")
        """
        data = self.raw(ftype=ftype)
        return gzip.compress(data.encode("utf-8"))

    def get_data(self, key=None, add_data=None):
        """
        Get the data of the TestSet.

        Parameters
        ----------
        key : str
            the key of the requested data (default None)
        add_data : dict
            the key of the requested data (default None)
        """
        if key is None:
            all_instances = {}
            self.load_children()
            instances = self.children.to_dict().keys()
            count = 0
            for i in instances:
                all_instances[i] = self.children[i].to_dict()
                if "instance_id" not in all_instances[i].keys():
                    all_instances[i]["instance_id"] = count
                    count = count + 1
                if "ProblemName" not in all_instances[i].keys():
                    all_instances[i]["ProblemName"] = all_instances[i]["instance_name"]
                if "TimeLimit" not in all_instances[i].keys():
                    all_instances[i]["TimeLimit"] = self.get_data("TimeLimit")
                if self.lp_solver_githash:
                    all_instances[i]["SpxGitHash"] = self.lp_solver_githash

                further_keys = [Key.GitHash, "CommitTime", Key.LPSolver, Key.LogFileName,
                        Key.Settings, "RubberbandMetaId", "Seed", "Permutation"]
                for fk in further_keys:
                    all_instances[i][fk] = self.get_data(fk)

                if add_data is not None:
                    for k, v in add_data.items():
                        all_instances[i][k] = v
            return all_instances

        if key == Key.LPSolver:
            return self.lp_solver + " " + self.lp_solver_version
        if key == Key.Settings:
            if self.settings_short_name is not None:
                return self.settings_short_name
            else:
                return "none"
        if key == Key.LogFileName:
            return self.filename
        if key == "RubberbandMetaId":
            return self.meta.id
        if key == "Seed":
            return self.seed or str(0)
        if key == "Permutation":
            return self.permutation or str(0)
        if key == "TimeLimit":
            return self.time_limit or str(0)
        if key == "CommitTime":
            return str(self.git_commit_timestamp)
        if key == "SpxGitHash":
            return self.lp_solver_githash or ""
        if key == Key.GitHash:
            return self.git_hash
        if key == "ReportVersion":
            return "\\{}~{}+\\{}~{}".format(str.lower(self.solver),
                    self.solver_version,
                    str.lower(self.lp_solver),
                    self.lp_solver_version)

    def json(self, ftype=".out"):
        """
        Return the data contained in the TestSet object as JSON.

        Parameters
        ----------
        ftype : str
            extension of file to get data from (default ".out")
        """
        if ftype == ".set":
            output = {}
            for k in list(self.settings):
                setting = getattr(self.settings, k)
                default = getattr(self.settings_default, k)

                if k in INFINITY_KEYS:
                    if setting == INFINITY_MASK:
                        setting = INFINITY_FLOAT
                    if default == INFINITY_MASK:
                        default = INFINITY_FLOAT

                output[k] = {
                    "setting": setting,
                    "default": default,
                }

            return json.dumps(output)

        elif ftype == ".out":
            all_instances = {self.test_set: {}}
            all_instances[self.test_set] = self.get_data()
            return json.dumps(all_instances, default=date_handler)

        elif ftype == ".err":
            # TODO
            raise NotImplemented()

    def csv(self, ftype=".out"):
        """
        Return the data contained in the TestSet object as CSV.

        Parameters
        ----------
        ftype : str
            extension of file to get data from (default ".out")
        """
        raise NotImplemented()

    def delete_all_associations(self):
        """Delete all children associated to a TestSet object, i.e. Result and File objects."""
        self.delete_all_children()
        self.delete_all_files()

    def delete_all_children(self):
        """Delete all children (Result objects) associated to a TestSet object."""
        self.load_children()
        for c_name in self.children:
            c = self.children[c_name]
            c.delete()

    def delete_all_files(self):
        """Delete all File objects associated to a TestSet object."""
        self.load_files()
        for ft in self.files:
            f = self.files[ft]
            f.delete()

    def load_children(self):
        """Load all children (Results objects) associated to a TestSet object."""
        s = Result.search()
        # it's generally discouraged to return a large number of elements from a search query
        s = s.filter("term", _parent=self.meta.id)
        self.children = {}

        # this uses pagination/scroll
        for hit in s.scan():
            self.children[hit.instance_name] = hit

    def load_files(self):
        """Load the files of a TestSet object."""
        s = File.search()
        s = s.filter("term", testset_id=self.meta.id)

        self.files = {}
        # this uses pagination/scroll
        for hit in s.scan():
            self.files[hit.type] = hit

    def load_stats(self, subset=[]):
        """
        Load the statistics of a TestSet object.

        Parameters
        ----------
        subset : list
            a subset of instance names to compute statistics for (default [])
        """
        self.stats = {}
        if not hasattr(self, "children"):
            self.load_children()

        if subset:
            all_instances = [self.children[instance_name] for instance_name in subset]
        else:
            all_instances = self.children.to_dict().values()

        self.stats = compute_stat(all_instances)


date_handler = lambda obj: (  # noqa
    obj.isoformat()
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date)
    else None
)
