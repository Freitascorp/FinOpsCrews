"""CLI entry point for crypto_pump_detector crew."""

from crypto_pump_detector.crew import CryptoPumpDetectorCrew


def run():
    CryptoPumpDetectorCrew().crew().kickoff(inputs={
        "min_market_cap": "500000",
        "max_market_cap": "5000000000",
        "volume_spike_threshold": "0.15",
        "top_n": "15",
    })


if __name__ == "__main__":
    run()
