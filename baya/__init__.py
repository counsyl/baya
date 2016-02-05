from _version import __version__

__version__  # silence codequality

from .membership import RolesNode
import permissions  # nopep8
from .permissions import requires

SetMembershipNode = RolesNode  # For backwards compatibility purposes.
requires
