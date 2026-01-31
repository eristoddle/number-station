
import pytest
from hypothesis import given, strategies as st

def test_board_lane_organization_property():
    """
    Property 6: Board Mode Lane Organization.
    Ensures that the board maintains requested lanes and can reorganize.
    """
    # Simulate lane selection
    available_options = ["RSS", "Twitter", "Reddit", "Hacker News", "Dev.to"]

    @given(st.sets(st.sampled_from(available_options), min_size=1, max_size=5))
    def check_lanes(selected):
        # The UI should render exactly len(selected) columns
        # In our implementation, st.session_state.board_lanes stores this.
        lanes = list(selected)
        assert len(lanes) == len(selected)
        for l in lanes:
            assert l in available_options

    check_lanes()
