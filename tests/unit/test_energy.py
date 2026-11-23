import pytest
from rncp_bc2.energy import joules, summary, CPU_TDP_W, PHYSICAL_CORES, MEMORY_W_PER_GB


def test_cpu_seconds_use_tdp_per_core():
    # 8 secondes CPU × (45 W / 8 cœurs) = 45 J, sans mémoire.
    assert joules(8.0) == pytest.approx(CPU_TDP_W / PHYSICAL_CORES * 8)


def test_memory_power_scales_with_wall_time_and_size():
    assert joules(0.0, wall_seconds=10.0, memory_gb=2.0) == pytest.approx(10 * 2 * MEMORY_W_PER_GB)


def test_summary_converts_to_wh_and_co2():
    result = summary(3600.0, carbon=20.0)
    assert result['wh'] == 1.0
    assert result['co2_g'] == pytest.approx(0.02)


def test_negative_inputs_are_refused():
    with pytest.raises(ValueError):
        joules(-1.0)
