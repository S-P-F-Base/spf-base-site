from include_routers import include_routers_from_package

from .profile import router as _root_profile
from .wiki.wiki_render import router as _root_wiki

router = include_routers_from_package(__name__)
router.include_router(_root_wiki)
router.include_router(_root_profile)
