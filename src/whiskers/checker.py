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


class BaseChecker(object):
    """Base class for version checkers

    attributes:

    index_url: url of an alternative package index
    only_final_versions: True (default) will not return alpha/beta/dev releases
    """
    __custom_url = False
    def __init__(self,
                 index_url=None,
                 only_final_versions=True,
                 ):
        self.only_final_versions = only_final_versions
        self.pi = package_index.PackageIndex(search_path=())
        self._set_index_url(index_url)
        if index_url is not None:
            self.__custom_url = True

    def _set_index_url(self, url):
        """set the index URL
        """
        if url is not None:
            self.pi.index_url = url
        if not self.pi.index_url.endswith('/'):
            self.pi.index_url += '/'

    def check(self, level=0):
        """Search new versions in a version list
        versions must be a dict {'name': 'version'}

        The new version is limited to the given level:
        Example with version x.y.z
        level = 0: checks new version x
        level = 1: checks new version y
        level = 2: checks new version z

        By default, the highest version is found.
        """
        versions = self.get_versions()
        new_versions = []

        for name, version in sorted(versions.items()):
            parsed_version = parse_version(version)
            req = Requirement.parse(name)
            self.pi.find_packages(req)
            new_dist = None
            # loop all index versions until we find the 1st newer version
            # that keeps the major versions (below level)
            # and (optionally and by default) is a final version
            for dist in self.pi[req.key]:
                if self.only_final_versions and _final_version(parsed_version) and not _final_version(dist.parsed_version):
                    #only skip non-final releases if the current release is a final one
                    continue
                # trunk the version tuple to the first `level` elements
                # (and remove *final and pad both to the level length)
                trunked_current = [x for x in parsed_version[:level]
                                   if not x.startswith('*')]
                trunked_candidate = [x for x in dist.parsed_version[:level]
                                     if not x.startswith('*')]
                while len(trunked_candidate) < level:
                    trunked_candidate.append('00000000')
                while len(trunked_current) < level:
                    trunked_current.append('00000000')
                # ok now we can compare: -> skip if we're still higher.
                if trunked_candidate > trunked_current:
                    continue
                new_dist = dist
                break

            if new_dist and new_dist.parsed_version > parsed_version:
                new_versions.append((name, new_dist.version))

        return new_versions

    def get_versions(self):
        """Get a dict {'name': 'version', ...} with package versions to check.
        This should be implemented by derived classes
        """
        raise NotImplementedError

