import pytest

pytest.importorskip("xgboost")

from ml_models.xgb_signal_classifier import XGBSignalClassifier
import pandas as pd


def test_classifier_initialization():
    clf = XGBSignalClassifier()
    assert clf.model is None


def test_prepare_features():
    clf = XGBSignalClassifier()
    df = pd.DataFrame({'close': [1,2,3,4,5,6,7,8,9,10]})
    features = clf.prepare_features(df)
    assert 'returns_1' in features.columns
