from fastapi import APIRouter
from api.v1.endpoints import auth, user, challenge, contribution, language, model_meta, storage

router = APIRouter()

# Include all routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(user.router, prefix="/user", tags=["User Management"])
router.include_router(challenge.router, prefix="/challenges", tags=["Challenges"])
# router.include_router(contribution.router, prefix="/contribution", tags=["Contributions"])
router.include_router(language.router, prefix="/language", tags=["Languages"])

# router.include_router(model_meta.router, prefix="/model-meta", tags=["Model Metadata"])
# router.include_router(points.router, prefix="/points", tags=["Points System"])
# router.include_router(storage.router, prefix="/storage", tags=["Storage"])
# router.include_router(vote.router, prefix="/vote", tags=["Voting"])
#
