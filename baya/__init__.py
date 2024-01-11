from __future__ import absolute_import
from ._version import __version__

__version__  # silence codequality

from .membership import RolesNode
from . import permissions  # noqa: F401
from .permissions import requires

SetMembershipNode = RolesNode  # For backwards compatibility purposes.
requires
