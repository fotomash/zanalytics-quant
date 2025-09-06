import xgboost as xgb
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
from typing import Dict, List, Tuple
import logging
from datetime import datetime


class XGBSignalClassifier:
    """XGBoost-based signal classifier for trading decisions
    Integrates with your existing confluence scoring system"""

    def __init__(self, config_path: str = "config/ml_config.yaml"):
        self.model = None
        self.feature_columns = None
        self.is_trained = False
        self.config = self._load_config(config_path)
        self.xgb_params = {
            'objective': 'multi:softprob',
            'num_class': 3,
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
        }

    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        features = data.copy()
        features['returns_1'] = features['close'].pct_change(1)
        features['returns_5'] = features['close'].pct_change(5)
        features['returns_20'] = features['close'].pct_change(20)
        features['volatility_5'] = features['returns_1'].rolling(5).std()
        features['volatility_20'] = features['returns_1'].rolling(20).std()
        features['rsi_14'] = self._calculate_rsi(features['close'], 14)
        features['sma_20'] = features['close'].rolling(20).mean()
        features['sma_50'] = features['close'].rolling(50).mean()
        features['sma_ratio'] = features['close'] / features['sma_20']
        if 'correlation_dxy_vix' in data.columns:
            features['correlation_crisis'] = (data['correlation_dxy_vix'] > 0.75).astype(int)
        for col in ['smc_score', 'wyckoff_score', 'volume']:
            if col in data.columns:
                if col == 'volume':
                    features['volume_sma'] = features['volume'].rolling(20).mean()
                    features['volume_ratio'] = features['volume'] / features['volume_sma']
                else:
                    features[col] = data[col]
        return features.dropna()

    def create_labels(self, data: pd.DataFrame, forward_periods: int = 5) -> pd.Series:
        forward_returns = data['close'].pct_change(forward_periods).shift(-forward_periods)
        buy_threshold = 0.02
        sell_threshold = -0.02
        labels = pd.Series(index=data.index, dtype=int)
        labels[forward_returns > buy_threshold] = 2
        labels[forward_returns < sell_threshold] = 0
        labels[(forward_returns >= sell_threshold) & (forward_returns <= buy_threshold)] = 1
        return labels

    def train(self, data: pd.DataFrame, target_column: str | None = None) -> Dict:
        logging.info("Starting XGBoost model training...")
        features_df = self.prepare_features(data)
        labels = data[target_column] if target_column else self.create_labels(data)
        common_index = features_df.index.intersection(labels.index)
        features_df = features_df.loc[common_index]
        labels = labels.loc[common_index]
        numeric_columns = features_df.select_dtypes(include=[np.number]).columns
        self.feature_columns = [c for c in numeric_columns if c not in ['close', 'open', 'high', 'low']]
        X = features_df[self.feature_columns]
        y = labels
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        self.model = xgb.XGBClassifier(**self.xgb_params)
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)
        performance = {
            'accuracy': float((y_pred == y_test).mean()),
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'feature_importance': dict(zip(self.feature_columns, self.model.feature_importances_)),
            'training_samples': len(X_train),
            'test_samples': len(X_test),
        }
        self.is_trained = True
        logging.info("Model training completed")
        return performance

    def predict_signal(self, features: pd.DataFrame) -> Dict:
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        features_prepared = self.prepare_features(features)
        X = features_prepared[self.feature_columns].iloc[-1:]
        probabilities = self.model.predict_proba(X)[0]
        predicted_class = self.model.predict(X)[0]
        signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        return {
            'signal': signal_map[predicted_class],
            'confidence': float(probabilities[predicted_class]),
            'probabilities': {
                'SELL': float(probabilities[0]),
                'HOLD': float(probabilities[1]),
                'BUY': float(probabilities[2]),
            },
            'timestamp': datetime.now().isoformat(),
        }

    def save_model(self, filepath: str):
        if not self.is_trained:
            raise ValueError("No trained model to save")
        model_data = {
            'model': self.model,
            'feature_columns': self.feature_columns,
            'config': self.config,
        }
        joblib.dump(model_data, filepath)
        logging.info(f"Model saved to {filepath}")

    def load_model(self, filepath: str):
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.feature_columns = model_data['feature_columns']
        self.config = model_data.get('config', {})
        self.is_trained = True
        logging.info(f"Model loaded from {filepath}")

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _load_config(self, config_path: str) -> Dict:
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {}


if __name__ == "__main__":
    classifier = XGBSignalClassifier()
    pass
