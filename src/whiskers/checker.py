from pkg_resources import parse_version, Requirement
from setuptools import package_index


_final_parts = '*final-', '*final'
def _final_version(parsed_version):
    """Function copied from zc.buildout.easy_install._final_version
    """
    for part in parsed_version:
        if (part[:1] == '*') and (part not in _final_parts):
            return False
    return True

import pip

class BaseChecker(pip.index.PackageFinder):
    """Base class for version checkers

    attributes:

    index_url: url of an alternative package index
    only_final_versions: True (default) will not return alpha/beta/dev releases
    """
    def __init__(self,
                 index_url=None,
                 only_final_versions=True,
                 ):
        super(BaseChecker, self).__init__([], [index_url], allow_all_prereleases=not only_final_versions)

    def check(self):
        versions = self.get_versions()
        last_versions = []

        for name, version in sorted(versions.items()):
            req = pip.req.InstallRequirement.from_line(name)
            try:
                link_info = self._link_package_versions(self.find_requirement(req, False), req.name)
            except pip.exceptions.DistributionNotFound:
                pass
            if len(link_info)>0:
                if link_info[0][2] != version:
                    last_versions.append((name, link_info[0][2]))

        return last_versions

    def get_versions(self):
        """Get a dict {'name': 'version', ...} with package versions to check.
        This should be implemented by derived classes
        """
        raise NotImplementedError

