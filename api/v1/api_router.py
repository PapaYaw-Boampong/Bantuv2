from fastapi import APIRouter
from api.v1.endpoints import auth, user, challenge, contribution, language, evaluation, samples, rewards, storage  

router = APIRouter()

# Include all routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

router.include_router(user.router, prefix="/user", tags=["User Management"])

router.include_router(challenge.router, prefix="/challenges", tags=["Challenges"])

router.include_router(contribution.router, prefix="/contributions", tags=["Contributions"])

router.include_router(samples.router, prefix="/samples", tags=["Samples"])

router.include_router(evaluation.router, prefix="/evaluations", tags=["Evaluations"])


router.include_router(rewards.router, prefix="/rewards", tags=["Rewards"])

router.include_router(language.router, prefix="/language", tags=["Languages"])

# router.include_router(model_meta.router, prefix="/model-meta", tags=["Model Metadata"])

router.include_router(storage.router, prefix="/storage", tags=["Storage"])


# router.include_router(vote.router, prefix="/vote", tags=["Voting"])

