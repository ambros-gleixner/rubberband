"""Contains ResultView."""
from tornado.web import HTTPError
import logging

from .base import BaseHandler
from rubberband.models import TestSet
from rubberband.utils import ResultClient, write_file
from rubberband.utils.helpers import setup_testruns_subst_dict, get_rbid_representation
from rubberband.constants import EXPORT_FILE_TYPES, IPET_EVALUATIONS


class ResultView(BaseHandler):
    """Request handler handling the results view."""

    def get(self, parent_id):
        """
        Answer to GET requests.

        Parameters
        ----------
        parent_id
            Rubberband id of parent
        """
        # parent id is the first argument: meta id of TestSet
        if not parent_id:
            raise HTTPError(404)
        parent = TestSet.get(id=parent_id, ignore=404)

        if not parent:
            raise HTTPError(404)

        # get data associated with TestSet, save in parent.children[]
        parent.load_children()

        compare = []
        comparelist = self.get_argument("compare", default=None)

        if comparelist:
            compare_ids = comparelist.split(",")
            compare = load_testsets(compare_ids)
            all_runs = [parent] + compare
            # save intersection results and difference results
            sets = get_intersection_difference([c.children.to_dict().keys() for c in all_runs])
        else:
            sets = {}

        # construct link to download archive
        testset_ids = []
        if compare:
            testset_ids = compare_ids
        testset_ids.append(parent_id)
        downloadziplink = "/download?testsets=" + (",".join(testset_ids))

        metas = [key for md in [parent] + compare for key in md.to_dict().get('metadata', [])]
        meta = list(set(metas))
        meta.sort()

        fileoptions = {}
        for ftype in EXPORT_FILE_TYPES:
            obj = TestSet.get(id=parent_id)
            file_contents = getattr(obj, "raw")(ftype=ftype)
            fileoptions[ftype] = (file_contents is not None)

        # sort testruns by their representation and render table
        # get substitutions dictionary
        testruns = [parent] + compare
        repres = setup_testruns_subst_dict(testruns)
        testruns = sorted(testruns,
                key=lambda x: repres['long'][get_rbid_representation(x, "extended")])

        rrt = self.render_string("results_table.html", results=testruns,
                representation=repres, tablename="rb-legend-table",
                checked=parent.meta.id, radiobuttons=True)

        self.render("result_view.html", file=parent, compare=compare, meta=meta,
                comparelist=comparelist, representation=repres, sets=sets,
                rendered_results_table=rrt, fileoptions=fileoptions,
                downloadzip=downloadziplink, evals=IPET_EVALUATIONS)

    def post(self, parent_id):
        """
        Answer to POST requests.

        Update the tags field
        """
        # parent id is the first argument: meta id of TestSet
        t = TestSet.get(id=parent_id)
        if not self.has_permission(t, "edit"):
            return self.write_error(status=403,
                    msg="Sorry, you do not have permission to edit this run.")

        next_url = "{}/result/{}".format(self.application.base_url, t.meta.id)
        tags = self.get_argument("tags-input", default=None)

        if tags is not None:
            tags = tags.split(",")
            t.tags = [tag.strip() for tag in tags]
            t.save()
        self.redirect(next_url)

    def put(self, parent_id):
        """
        Answer to PUT requests.

        Update/Reimport TestSet (with IPET)

        Parameters
        ----------
        parent_id
            id of TestSet to update.
        """
        t = TestSet.get(id=parent_id)
        if not self.has_permission(t, "edit"):
            return self.write_error(status=403,
                    msg="Sorry, you do not have permission to reimport this run.")

        t.load_files()
        if "out" not in t.files.to_dict().keys():
            raise HTTPError(404)
            return
        t.delete_all_children()

        # write all files to local directory
        paths = []
        for k in t.files:
            paths.append(write_file(t.files[k].filename, str.encode(t.files[k].text)))
        paths = tuple(paths)

        c = ResultClient(user=self.current_user)
        c.reimport_files(paths, t)

        msg = "{} updated by {}".format(t.meta.id, self.current_user)
        logging.info(msg)

    def delete(self, parent_id):
        """
        Answer to DELETE requests.

        Delete the TestSet and all associated Results in Elasticsearch.

        Parameters
        ----------
        parent_id
            id of TestSet to delete.
        """
        t = TestSet.get(id=parent_id)

        if not self.has_permission(t, "delete"):
            return self.write_error(status=403,
                    msg="Sorry, you do not have permission to delete this run.")

        # remove from db
        t.delete_all_associations()
        t.delete()

        msg = "{} deleted {}".format(self.current_user, t.meta.id)
        logging.info(msg)


def load_testsets(ids):
    """
    Load TestSets and their associated Results.

    Parameters
    ----------
    ids : list
        List of ids of TestSets

    Returns
    -------
    list
        List of TestSets
    """
    tss = []
    try:
        for id in ids:
            t = TestSet.get(id=id)
            t.load_children()
            tss.append(t)
    except:
        raise HTTPError(404)

    return tss


def get_same_status(runs):
    """
    Get a list of instance names that have the same status in all given TestSets.

    Parameters
    ----------
    runs
        set of TestSets

    Returns
    -------
    list
        list of names of instances whose status is the same in all TestSets.
    """
    instances = runs[0].children.to_dict()
    final_instances = set([])
    for i in instances:
        statuses = []
        for r in runs:
            rd = r.children.to_dict()
            if i in rd and "Status" in rd[i]:
                statuses.append(rd[i]["Status"])

        if len(statuses) == len(runs) and len(set(statuses)) == 1:
            final_instances.add(i)

    return final_instances


def get_intersection_difference(runs):
    """
    Get the intersection and difference of a list of lists.

    Parameters
    ----------
    runs
        set of TestSets

    Returns
    -------
    dict
        Key "intersection" : list of Results present in all given TestSets,
        Key "difference" : list of Results present in at least one given TestSet but not in all.
    """
    intersection = set(runs[0])
    difference = set()

    for r in runs:
        intersection = intersection & r
        difference.update(r)

    difference -= intersection

    return {
                "intersection": intersection,
                "difference": difference,
            }
