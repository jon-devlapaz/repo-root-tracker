"""Run the unchanged headed performance assertions against a chosen HTML snapshot.

RRT_REFERENCE_PERF=1 PYTHONPATH=src python tests/bonsai_performance_review.py --dashboard FILE
The regular product runner remains tests/test_board_performance.py.
"""
import argparse
from pathlib import Path
import pytest
import test_board_performance

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dashboard',type=Path,required=True)
    args=parser.parse_args()
    test_board_performance.DASHBOARD=args.dashboard.resolve(strict=True)
    raise SystemExit(pytest.main([str(Path(__file__).with_name('test_board_performance.py')),'-q','-s']))
