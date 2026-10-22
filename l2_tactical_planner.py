import os
import time
import datetime

from lite_world_model import WorldBuilder

from config import LLM_ENABLED, USE_FALLBACK_ON_ERROR
from config import LLM_DEBUG
from decision_validator import (
    DecisionValidationError,
    parse_llm_response,
    validate_action,
)
from fallback_guidance import FallbackGuidance
from llm_decision import TacticalLLMDecisionMaker
from rover_interfaces import TacticalAction
from perception_module import PerceptionResult

from utils.xlogger import XLogger

class L2TacticalPlanner:
    def __init__(
        self,
        rover_client,
        perception_module,
        world_builder,
        llm_enabled: bool = LLM_ENABLED,
        fallback_enabled: bool = USE_FALLBACK_ON_ERROR,
        human_on_loop: bool = True,
    ):
        self.rover_client = rover_client
        self.perception_module = perception_module
        self.llm_enabled = llm_enabled
        self.fallback_enabled = fallback_enabled
        self.human_on_loop = human_on_loop
        self.llm = TacticalLLMDecisionMaker()
        self.fallback = FallbackGuidance()
        # Operator approval state used by supervised field tests
        self.last_action_approved = True
         # 📁 carpeta única por ejecución
        #run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        #self.output_dir = f"simulaciones/{run_id}"
        #os.makedirs(self.output_dir, exist_ok=True)
        # 🔢 contador global
        #self.sim_counter = 0

    def _build_gpt_navigation_prompt(self, perception_state, l3_task):
        directions = {}
        for region in (perception_state.regions or []):
            if isinstance(region, dict) and region.get("name") in ("left", "front", "right"):
                if type(region.get("traversable")) is bool:
                    directions[region["name"]] = region["traversable"]

        if set(directions) != {"left", "front", "right"}:
            raise ValueError("Incomplete three-sector perception")

        return f"""
You are the tactical navigation controller of a ground rover.

Navigate toward the target while avoiding obstacles.
The target heading is a preference, not an obligation on every cycle.
You may temporarily follow another passable corridor to go around obstacles.
Choose a short local maneuver. Perception will be refreshed after each maneuver.

Never choose a blocked corridor.
Never reverse.
If no useful safe movement is possible, choose HOLD.

NAVIGATION:
heading_error_deg={l3_task.get("heading_error_deg")}
distance_remaining_m={l3_task.get("distance_remaining_m")}

TRAVERSABLE CORRIDORS:
left={str(directions["left"]).lower()}
front={str(directions["front"]).lower()}
right={str(directions["right"]).lower()}
confidence={perception_state.confidence}

Return exactly ONE action:
MOVE_FORWARD
FORWARD_LEFT
FORWARD_RIGHT
HOLD
""".strip()

    @staticmethod
    def _normalize_llm_token(raw_response: str) -> str:
        token = raw_response.strip()
        if token.startswith("ACTION="):
            token = token[len("ACTION="):].strip()
        return token.splitlines()[0].strip()

    def decide_action_with_llm(self, rover_state, perception_state, image_bytes, l3_task, gps_state):
        XLogger.log("L2", "Decide action with GPT tactical navigation ...")

        if perception_state is None:
            raise RuntimeError("Perception state unavailable")

        if l3_task.get("heading_error_deg") is None:
            XLogger.log("L2", "Missing heading -> HOLD")
            raw_response = "ACTION=HOLD"
            prompt = "DETERMINISTIC_MISSING_HEADING"

        elif perception_state.confidence <= 0.3:
            XLogger.log("L2", "LOW confidence -> HOLD")
            raw_response = "ACTION=HOLD"
            prompt = "DETERMINISTIC_LOW_CONFIDENCE"

        else:
            prompt = self._build_gpt_navigation_prompt(perception_state, l3_task)
            gpt_raw = self.llm.decide(prompt)
            result = self._normalize_llm_token(gpt_raw)

            if result not in {"MOVE_FORWARD", "FORWARD_LEFT", "FORWARD_RIGHT", "HOLD"}:
                raise ValueError(f"Invalid GPT tactical result: {result!r}")

            XLogger.log("L2", f"GPT tactical result: {result}")
            raw_response = f"ACTION={result}"

        parsed_action = parse_llm_response(raw_response)

        validated_action = validate_action(
            parsed_action,
            rover_state,
            perception_state,
        )

        XLogger.log("L2", f"Validated action: {validated_action.value}")

        return validated_action, raw_response, prompt

    def decide_action(self, rover_state, perception_state, image_bytes, l3_task, gps_state):
        XLogger.log("L2", "Decide_action...")
        if not self.llm_enabled:
            return TacticalAction.HOLD, "GPT_DISABLED_HOLD", None, "safety_hold"
        try:

            action, raw_response, prompt = self.decide_action_with_llm(
                rover_state,
                perception_state,
                image_bytes,
                l3_task,
                gps_state,
            )



            return action, raw_response, prompt, "llm"

        except (DecisionValidationError, RuntimeError, ValueError) as exc:
            #print(f"[GUIDANCE] LLM decision failed: {exc}")
            XLogger.log("L2", f"[GUIDANCE] LLM decision failed: {exc}")
            if self.fallback_enabled:
                # GPT-only experiment: never switch to heuristic motion after API errors.
                return TacticalAction.HOLD, f"GPT_ERROR_HOLD: {exc}", None, "safety_hold"

            raise

    def step(self, rover_state, result, l3_task, observability=None):
        XLogger.log("L2", "step")

        # 🔢 incrementar contador global
        #self.sim_counter += 1
        #sim_id = self.sim_counter
        # 💾 guardar imagen
        #if image_bytes is not None:
        #    filename = f"{sim_id:04d}.jpg"
        #    filepath = os.path.join(self.output_dir, filename)
        #with open(filepath, "wb") as f:
        #    f.write(image_bytes)
        #XLogger.log("L2", f"step [SIM {sim_id:04d}] Image saved → {filepath}")
        semantic_summary = (
            result.world_model.semantic_summary()
            if result.world_model is not None
            else "World model unavailable"
        )
        #XLogger.log("L2", "step: " + s)

        action, decision_info, prompt, source = self.decide_action(
            rover_state,
            result.perception_state,
            result.image_bytes,
            l3_task,
            result.gps_state,
        )

        action = self._apply_safety_envelope(
            action,
            result.perception_state,
        )

        # Compact pre-action observability for field tests.
        if observability is not None:
            nav = observability["navigation_state"]
            guidance = observability["guidance_task"]
            perception = result.perception_state

            XLogger.log(
                "CYCLE",
                (
                    "\n========== TACTICAL CYCLE ==========\n"
                    "PERCEPTION\n"
                    f"  obstacle_ahead : {perception.obstacle_ahead}\n"
                    f"  free_direction : {perception.free_direction}\n"
                    f"  confidence     : {perception.confidence}\n"
                    f"  summary        : {semantic_summary}\n"
                    "\n"
                    "NAVIGATION\n"
                    f"  position       : {nav.latitude}, {nav.longitude}\n"
                    f"  gps_accuracy   : {observability['position_accuracy_m']} m\n"
                    f"  heading        : {nav.heading_deg} deg\n"
                    f"  position_fresh : {observability['position_fresh']}\n"
                    f"  heading_fresh  : {observability['heading_fresh']}\n"
                    "\n"
                    "GUIDANCE\n"
                    f"  target_bearing : {guidance.desired_heading_deg} deg\n"
                    f"  heading_error  : {guidance.heading_error_deg} deg\n"
                    f"  distance       : {guidance.distance_remaining_m} m\n"
                    "\n"
                    "TACTICAL\n"
                    f"  action         : {action.value}\n"
                    "===================================="
                ),
            )


        #if LLM_DEBUG:
        #    print("\n=== Guidance Step ===")
        #    print(f"Rover state: {rover_state}")
        #    print(f"Perception: {perception_state}")
        #    print(f"Decision source: {source}")
        #    print(f"Decision info: {decision_info}")
        #    print(f"Chosen action: {action.value}")

        # 🔐 HUMAN-ON-THE-LOOP APPROVAL
        if self.human_on_loop:
            approved = self._request_user_approval(action, l3_task)
        else:
            approved = True

        self.last_action_approved = approved

        if approved:
            self.rover_client.execute_tactical_action(action)
        else:
            XLogger.log("L2", "[USER] Action rejected → HOLD")
            action = TacticalAction.HOLD
            self.rover_client.execute_tactical_action(action)

        return action, decision_info, prompt, source

    def _apply_safety_envelope(self, action, perception_state):
        """
        Hard local safety veto.

        This layer does not choose a better maneuver.
        It only prevents a commanded maneuver when perception
        reports an immediate non-traversable obstacle inside
        the maneuver side.

        If a maneuver is vetoed, return HOLD so L2 can reason
        again on the next cycle.
        """

	# SAFETY: stop whenever perception is unavailable.
        if perception_state is None or perception_state.confidence <= 0.0:
            XLogger.log(
                "L2",
                "[SAFETY] Perception unavailable -> STOP"
            )
            return TacticalAction.STOP

        # Three-sector GPT V3.2 safety: stop manoeuvres that contradict perception.
        # Never authorize an automatic reverse from monocular forward vision.
        if action == TacticalAction.MOVE_BACKWARD:
            return TacticalAction.HOLD

        if perception_state.confidence <= 0.3:
            return TacticalAction.HOLD

        directions = {}
        for region in (perception_state.regions or []):
            if isinstance(region, dict) and region.get("name") in ("left", "front", "right"):
                if type(region.get("traversable")) is bool:
                    directions[region["name"]] = region["traversable"]

        # Fail closed if the new perception contract is incomplete.
        if set(directions) != {"left", "front", "right"}:
            XLogger.log("L2", "[SAFETY] Missing GPT corridor data -> HOLD")
            return TacticalAction.HOLD

        permitted = {
            TacticalAction.MOVE_FORWARD: directions["front"],
            TacticalAction.FORWARD_LEFT: directions["left"],
            TacticalAction.FORWARD_RIGHT: directions["right"],
        }
        if action in permitted and not permitted[action]:
            XLogger.log("L2", f"[SAFETY] GPT corridor veto -> {action.value}")
            return TacticalAction.HOLD

        # Only moving/steering actions need this first safety check.
        if action not in (
            TacticalAction.MOVE_FORWARD,
            TacticalAction.FORWARD_LEFT,
            TacticalAction.FORWARD_RIGHT,
        ):
            return action

        # Perception defines 0.0-0.5 m as the IMMEDIATE band.
        immediate_distance_m = 0.5

        objects = perception_state.objects or []

        for obj in objects:
            if not isinstance(obj, dict):
                continue

            # We only act on explicit non-traversable objects.
            if obj.get("traversable") is not False:
                continue

            distance = obj.get("distance_m")

            try:
                distance = float(distance)
            except (TypeError, ValueError):
                continue

            if distance > immediate_distance_m:
                continue

            position = obj.get("position", {})

            if isinstance(position, dict):
                region = position.get("region")
            else:
                # Defensive compatibility with older/simple perception schemas.
                region = position

            blocked = False

            if action == TacticalAction.MOVE_FORWARD:
                blocked = region == "front"

            elif action == TacticalAction.FORWARD_LEFT:
                blocked = region in ("left", "front-left")

            elif action == TacticalAction.FORWARD_RIGHT:
                blocked = region in ("right", "front-right")

            if blocked:
                XLogger.log(
                    "L2",
                    "[SAFETY] Veto "
                    f"{action.value}: "
                    f"{obj.get('type', 'object')} "
                    f"in region={region}, "
                    f"distance={distance:.2f}m, "
                    f"risk={obj.get('risk_level', 'unknown')}"
                )

                return TacticalAction.HOLD

        return action

    def _request_user_approval(self, action, l3_task):
        try:
            target_heading = l3_task.get("desired_heading_deg")
            heading_error = l3_task.get("heading_error_deg")
            distance = l3_task.get("distance_remaining_m")

            rover_heading = None

            if target_heading is not None and heading_error is not None:
                rover_heading = (target_heading - heading_error) % 360.0

            def fmt_deg(value):
                return "UNKNOWN" if value is None else f"{value:.1f}°"

            def fmt_error(value):
                return "UNKNOWN" if value is None else f"{value:+.1f}°"

            def fmt_distance(value):
                return "UNKNOWN" if value is None else f"{value:.1f} m"

            print()
            print("=" * 60)
            print("NAVIGATION DECISION")
            print(f"Target bearing : {fmt_deg(target_heading)}")
            print(f"Rover heading  : {fmt_deg(rover_heading)}")
            print(f"Heading error  : {fmt_error(heading_error)}")
            print(f"Distance       : {fmt_distance(distance)}")
            print(f"Action         : {action.value}")
            print("=" * 60)

            user_input = input(
                "Execute? [y = YES / any other key = STOP]: "
            ).strip().lower()

            return user_input in ("y", "yes")

        except KeyboardInterrupt:
            XLogger.log("L2", "[USER] Interrupted → rejecting action")
            return False

    def run_loop(self, steps=10, delay_s=1.0):
        i=0
        for _ in range(steps):
            XLogger.log("L2", f"[LOOP] Loop {i+1}/{Loops}")

            i=i+1
            self.step()
            time.sleep(delay_s)

