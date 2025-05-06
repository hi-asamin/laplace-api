from fastapi import APIRouter, Depends

from app.api.dependencies import get_simulation_service
from app.schemas.simulation import SimulationRequest, SimulationResponse

router = APIRouter(
    prefix="/simulation",
    tags=["simulation"],
    responses={404: {"description": "Not found"}},
)

@router.post("", response_model=SimulationResponse)
def simulate(
    req: SimulationRequest,
    sim_service = Depends(get_simulation_service)
):
    """
    モンテカルロシミュレーションを実行する
    """
    sims = sim_service.monte_carlo(req.symbol, req.years, req.simulations)
    return SimulationResponse(symbol=req.symbol, scenarios=sims) 