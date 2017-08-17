from ipet.misc import listGetShiftedGeometricMean as shmean
from ipet.misc import listGetGeomMean as gemean
from rubberband.constants import NONE_DISPLAY

from collections import OrderedDict


def compute_stat(instances):
    '''
    Computes statistical information about a list of instances.
        instances (list)
    # TODO this whole method is going to be replaced by ipet?
    '''
    stats = {}
    stats["all"] = OrderedDict()
    stats["all"]["instances"] = instances
    # group instances into status buckets
    for i in instances:
        # TODO this is probably not going to work with the new ipet
        status = i.Status.lower()
        if status.startswith("fail"):
            if "fail" not in stats:
                stats["fail"] = OrderedDict()
                stats["fail"]["instances"] = []
            stats["fail"]["instances"].append(i)
        elif status not in stats:
            # TODO isn't this overwriting the existing stats[status]?
            stats[status] = OrderedDict()
            stats[status]["instances"] = [i]
        else:
            stats[status]["instances"].append(i)

    keys = [
        # TODO update to new ipet
        "Nodes",
        "TotalTime_solving",
    ]
    for status in stats:
        stats[status]["count"] = len(stats[status]["instances"])

        for component in keys:
            stats[status][component] = OrderedDict()
            all_component = [getattr(i, component, None) for i in stats[status]["instances"]]

            if any(n is None for n in all_component):
                stats[status][component]["Total"] = NONE_DISPLAY
                stats[status][component]["Geomean"] = NONE_DISPLAY
                stats[status][component]["Shifted Geomean (10)"] = NONE_DISPLAY
            else:
                stats[status][component]["Total"] = round(sum(all_component), 3)
                stats[status][component]["Geomean"] = round(gemean(all_component), 3)
                stats[status][component]["shifted Geomean (10)"] = round(shmean(all_component,
                                                                                shiftby=10.0), 3)

        del(stats[status]["instances"])

    return stats
