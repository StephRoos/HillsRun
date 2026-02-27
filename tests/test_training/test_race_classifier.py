"""Tests for race classification."""
from src.training.race_classifier import classify_race
from src.training.models import RaceCategory


def test_trail_court():
    flags = classify_race(distance_km=30, elevation_gain_m=1500)
    assert flags.category == RaceCategory.trail_court
    assert not flags.is_ultra


def test_trail_moyen():
    flags = classify_race(distance_km=55, elevation_gain_m=3000)
    assert flags.category == RaceCategory.trail_moyen


def test_ultra():
    flags = classify_race(distance_km=100, elevation_gain_m=5000)
    assert flags.category == RaceCategory.ultra
    assert flags.is_ultra


def test_ultra_longue():
    flags = classify_race(distance_km=170, elevation_gain_m=10000)
    assert flags.category == RaceCategory.ultra_longue
    assert flags.is_ultra


def test_high_dplus():
    """60 m/km ratio threshold."""
    flags = classify_race(distance_km=50, elevation_gain_m=3500)
    assert flags.high_dplus  # 70 m/km > 60


def test_not_high_dplus():
    flags = classify_race(distance_km=50, elevation_gain_m=2000)
    assert not flags.high_dplus  # 40 m/km < 60


def test_technical():
    flags = classify_race(distance_km=30, elevation_gain_m=1000, technical_percent=50)
    assert flags.technical


def test_high_altitude():
    flags = classify_race(distance_km=30, elevation_gain_m=1000, altitude_max_m=3000)
    assert flags.high_altitude


def test_utmb():
    """Real race: UTMB 171km, 10000m D+. Ratio = 58.5 m/km (below 60 threshold)."""
    flags = classify_race(distance_km=171, elevation_gain_m=10000, technical_percent=20, altitude_max_m=2600)
    assert flags.category == RaceCategory.ultra_longue
    assert flags.is_ultra
    assert not flags.high_dplus  # 58.5 m/km < 60
    assert flags.high_altitude


def test_marathon_trail():
    """Trail marathon: 42km, 1800m D+."""
    flags = classify_race(distance_km=42, elevation_gain_m=1800)
    assert flags.category == RaceCategory.trail_moyen
    assert not flags.is_ultra
