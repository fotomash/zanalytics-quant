# tick_vectorizer.py
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler
import hashlib

@dataclass
class TickVector:
    timestamp: pd.Timestamp
    embedding: np.ndarray
    metadata: Dict
    tick_hash: str

class TickVectorizer:
    def __init__(self, config: Dict):
        self.config = config
        self.embedding_dim = config['tick_vectorizer']['embedding_dim']
        self.scaler = StandardScaler()
        self.feature_history = []
        self.vector_store = {}
        
    def extract_microstructure_features(self, df: pd.DataFrame, idx: int, window: int = 20) -> np.ndarray:
        """Extract microstructure features at tick level"""
        start_idx = max(0, idx - window)
        window_data = df.iloc[start_idx:idx+1]
        
        features = []
        
        # Spread dynamics (20 dims)
        spread_features = [
            window_data['spread'].mean(),
            window_data['spread'].std(),
            window_data['spread'].min(),
            window_data['spread'].max(),
            window_data['spread'].iloc[-1] / (window_data['spread'].mean() + 1e-9),
            window_data['spread'].diff().mean(),
            window_data['spread'].diff().std(),
            (window_data['spread'] > window_data['spread'].mean()).sum() / len(window_data),
            window_data['spread'].autocorr(lag=1) if len(window_data) > 1 else 0,
            window_data['spread'].autocorr(lag=5) if len(window_data) > 5 else 0,
        ]
        features.extend(spread_features[:10])
        features.extend([0] * (20 - len(spread_features)))
        
        # Volume profile (30 dims)
        if 'inferred_volume' in window_data.columns:
            vol_features = [
                window_data['inferred_volume'].mean(),
                window_data['inferred_volume'].std(),
                window_data['inferred_volume'].sum(),
                window_data['inferred_volume'].iloc[-1] / (window_data['inferred_volume'].mean() + 1e-9),
                window_data['inferred_volume'].quantile(0.25),
                window_data['inferred_volume'].quantile(0.75),
                window_data['inferred_volume'].skew(),
                window_data['inferred_volume'].kurt(),
                (window_data['inferred_volume'] > window_data['inferred_volume'].mean()).sum() / len(window_data),
                window_data['inferred_volume'].max() / (window_data['inferred_volume'].mean() + 1e-9),
            ]
            features.extend(vol_features[:10])
            features.extend([0] * (30 - len(vol_features)))
        else:
            features.extend([0] * 30)
            
        # Price velocity (20 dims)
        price_changes = window_data['price_mid'].diff()
        price_features = [
            price_changes.mean(),
            price_changes.std(),
            price_changes.abs().mean(),
            window_data['price_mid'].pct_change().mean(),
            window_data['price_mid'].pct_change().std(),
            (price_changes > 0).sum() / len(price_changes),
            price_changes.autocorr(lag=1) if len(price_changes) > 1 else 0,
            window_data['price_mid'].rolling(5).std().mean() if len(window_data) > 5 else 0,
            window_data['price_mid'].ewm(span=5).mean().iloc[-1] - window_data['price_mid'].mean(),
            np.polyfit(range(len(window_data)), window_data['price_mid'], 1)[0] if len(window_data) > 1 else 0,
        ]
        features.extend(price_features[:10])
        features.extend([0] * (20 - len(price_features)))
        
        return np.array(features)
    
    def extract_regime_features(self, df: pd.DataFrame, idx: int) -> np.ndarray:
        """Extract regime and market state features"""
        features = []
        
        # VPIN and toxicity (10 dims)
        if 'vpin' in df.columns:
            vpin_features = [
                df['vpin'].iloc[idx],
                df['vpin'].rolling(10).mean().iloc[idx] if idx >= 10 else df['vpin'].iloc[:idx+1].mean(),
                df['vpin'].rolling(10).std().iloc[idx] if idx >= 10 else df['vpin'].iloc[:idx+1].std(),
                (df['vpin'] > 0.5).rolling(10).sum().iloc[idx] / 10 if idx >= 10 else 0,
                (df['vpin'] > 0.7).rolling(10).sum().iloc[idx] / 10 if idx >= 10 else 0,
            ]
            features.extend(vpin_features[:5])
            features.extend([0] * (10 - len(vpin_features)))
        else:
            features.extend([0] * 10)
            
        # Market regime encoding (5 dims one-hot)
        regime_map = {'normal': [1,0,0,0,0], 'stressed': [0,1,0,0,0], 
                      'manipulated': [0,0,1,0,0], 'breakdown': [0,0,0,1,0], 'unknown': [0,0,0,0,1]}
        regime = df.get('regime', 'unknown') if isinstance(df, dict) else 'unknown'
        features.extend(regime_map.get(regime, regime_map['unknown']))
        
        return np.array(features)
    
    def extract_temporal_features(self, df: pd.DataFrame, idx: int) -> np.ndarray:
        """Extract temporal and burst pattern features"""
        features = []
        
        # Time-based features (15 dims)
        timestamp = df['timestamp'].iloc[idx]
        time_features = [
            timestamp.hour / 24.0,
            timestamp.minute / 60.0,
            timestamp.second / 60.0,
            timestamp.dayofweek / 6.0,
            np.sin(2 * np.pi * timestamp.hour / 24),
            np.cos(2 * np.pi * timestamp.hour / 24),
            np.sin(2 * np.pi * timestamp.minute / 60),
            np.cos(2 * np.pi * timestamp.minute / 60),
        ]
        
        # Tick burst patterns
        if 'tick_rate' in df.columns and idx > 0:
            tick_features = [
                df['tick_rate'].iloc[idx],
                df['tick_rate'].rolling(10).mean().iloc[idx] if idx >= 10 else df['tick_rate'].iloc[:idx+1].mean(),
                df['tick_rate'].rolling(10).std().iloc[idx] if idx >= 10 else df['tick_rate'].iloc[:idx+1].std(),
                df['tick_rate'].rolling(10).max().iloc[idx] if idx >= 10 else df['tick_rate'].iloc[:idx+1].max(),
            ]
            time_features.extend(tick_features[:4])
        
        features.extend(time_features[:15])
        features.extend([0] * (15 - len(time_features)))
        
        return np.array(features)
    
    def create_embedding(self, df: pd.DataFrame, idx: int) -> np.ndarray:
        """Create 1536-dim embedding from tick data"""
        # Extract base features (100 dims)
        micro_features = self.extract_microstructure_features(df, idx)  # 70 dims
        regime_features = self.extract_regime_features(df, idx)  # 15 dims  
        temporal_features = self.extract_temporal_features(df, idx)  # 15 dims
        
        base_features = np.concatenate([micro_features, regime_features, temporal_features])
        
        # Project to 1536 dims using random projection for remaining dims
        if len(self.feature_history) == 0:
            # Initialize projection matrix
            np.random.seed(42)
            self.projection_matrix = np.random.randn(len(base_features), self.embedding_dim - len(base_features))
            self.projection_matrix /= np.sqrt(len(base_features))
        
        # Create high-dim representation
        projected_features = np.dot(base_features, self.projection_matrix)
        embedding = np.concatenate([base_features, projected_features])
        
        # L2 normalize
        embedding = embedding / (np.linalg.norm(embedding) + 1e-9)
        
        return embedding
    
    def vectorize_tick_batch(self, df: pd.DataFrame, start_idx: int = 0, 
                           batch_size: int = 100) -> List[TickVector]:
        """Vectorize a batch of ticks"""
        vectors = []
        
        end_idx = min(start_idx + batch_size, len(df))
        
        for idx in range(start_idx, end_idx):
            # Create embedding
            embedding = self.create_embedding(df, idx)
            
            # Create metadata
            metadata = {
                'price': df['price_mid'].iloc[idx],
                'spread': df['spread'].iloc[idx],
                'volume': df.get('inferred_volume', pd.Series([100])).iloc[idx],
                'vpin': df.get('vpin', pd.Series([0])).iloc[idx],
                'tick_rate': df.get('tick_rate', pd.Series([1])).iloc[idx],
            }
            
            # Create hash for deduplication
            tick_hash = hashlib.md5(
                f"{df['timestamp'].iloc[idx]}_{df['bid'].iloc[idx]}_{df['ask'].iloc[idx]}".encode()
            ).hexdigest()
            
            vector = TickVector(
                timestamp=df['timestamp'].iloc[idx],
                embedding=embedding,
                metadata=metadata,
                tick_hash=tick_hash
            )
            
            vectors.append(vector)
            self.vector_store[tick_hash] = vector
            
        return vectors
    
    def find_similar_ticks(self, query_vector: TickVector, k: int = 10) -> List[Tuple[TickVector, float]]:
        """Find k most similar historical ticks using cosine similarity"""
        similarities = []
        
        for tick_hash, stored_vector in self.vector_store.items():
            if tick_hash != query_vector.tick_hash:
                similarity = np.dot(query_vector.embedding, stored_vector.embedding)
                similarities.append((stored_vector, similarity))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:k]
    
    def detect_anomalies(self, vectors: List[TickVector], threshold: float = 0.95) -> List[TickVector]:
        """Detect anomalous ticks based on vector similarity"""
        anomalies = []
        
        for vector in vectors:
            similar_ticks = self.find_similar_ticks(vector, k=20)
            
            if similar_ticks:
                avg_similarity = np.mean([sim for _, sim in similar_ticks])
                
                if avg_similarity < threshold:
                    anomalies.append(vector)
        
        return anomalies

# dashboard_integration.py
class VectorizedDashboard:
    def __init__(self, vectorizer: TickVectorizer):
        self.vectorizer = vectorizer
        self.session_vectors = []
        self.anomaly_buffer = []
        
    def update_tick_vectors(self, df: pd.DataFrame, dashboard_state: Dict) -> Dict:
        """Update dashboard with vectorized tick data"""
        # Get latest ticks to vectorize
        last_processed = dashboard_state.get('last_vectorized_idx', 0)
        
        if len(df) > last_processed:
            # Vectorize new ticks
            new_vectors = self.vectorizer.vectorize_tick_batch(
                df, start_idx=last_processed, 
                batch_size=min(100, len(df) - last_processed)
            )
            
            self.session_vectors.extend(new_vectors)
            
            # Detect anomalies
            anomalies = self.vectorizer.detect_anomalies(new_vectors)
            self.anomaly_buffer.extend(anomalies)
            
            # Update dashboard state
            dashboard_state['last_vectorized_idx'] = len(df)
            dashboard_state['total_vectors'] = len(self.session_vectors)
            dashboard_state['anomaly_count'] = len(self.anomaly_buffer)
            
            # Calculate vector statistics
            embeddings = np.array([v.embedding for v in new_vectors])
            dashboard_state['vector_stats'] = {
                'mean_norm': np.mean(np.linalg.norm(embeddings, axis=1)),
                'std_norm': np.std(np.linalg.norm(embeddings, axis=1)),
                'avg_similarity': self._calculate_avg_similarity(new_vectors),
            }
            
        return dashboard_state
    
    def _calculate_avg_similarity(self, vectors: List[TickVector]) -> float:
        """Calculate average pairwise similarity"""
        if len(vectors) < 2:
            return 1.0
            
        similarities = []
        for i in range(min(len(vectors), 20)):
            for j in range(i+1, min(len(vectors), 20)):
                sim = np.dot(vectors[i].embedding, vectors[j].embedding)
                similarities.append(sim)
                
        return np.mean(similarities) if similarities else 1.0
    
    def render_vector_analytics(self, st):
        """Render vector analytics in streamlit dashboard"""
        st.markdown("### 🧬 Vector Analytics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total Vectors", len(self.session_vectors))
        col2.metric("Vector Anomalies", len(self.anomaly_buffer))
        col3.metric("Avg Similarity", f"{self._calculate_avg_similarity(self.session_vectors[-100:]):.3f}")
        col4.metric("Memory Usage", f"{len(self.vectorizer.vector_store)} vectors")
        
        # Show recent anomalies
        if self.anomaly_buffer:
            st.markdown("#### Recent Anomalies")
            anomaly_data = []
            for anomaly in self.anomaly_buffer[-10:]:
                anomaly_data.append({
                    'timestamp': anomaly.timestamp,
                    'price': anomaly.metadata['price'],
                    'spread': anomaly.metadata['spread'],
                    'vpin': anomaly.metadata['vpin'],
                })
            st.dataframe(pd.DataFrame(anomaly_data))

# Integration code for existing dashboard
def integrate_vectorizer(analyzer, df, st):
    """Add this to your existing dashboard code"""
    
    # Initialize vectorizer
    vectorizer_config = {
        'tick_vectorizer': {
            'embedding_dim': 1536,
            'feature_extractors': ['microstructure', 'regime', 'temporal']
        }
    }
    
    vectorizer = TickVectorizer(vectorizer_config)
    vector_dashboard = VectorizedDashboard(vectorizer)
    
    # Update session state
    if 'vector_state' not in st.session_state:
        st.session_state.vector_state = {
            'last_vectorized_idx': 0,
            'total_vectors': 0,
            'anomaly_count': 0
        }
    
    # Process new ticks
    st.session_state.vector_state = vector_dashboard.update_tick_vectors(
        df, st.session_state.vector_state
    )
    
    # Add vector analytics section to dashboard
    with st.expander("🧬 Tick Vector Analysis", expanded=True):
        vector_dashboard.render_vector_analytics(st)
        
        # Vector similarity heatmap
        if len(vector_dashboard.session_vectors) > 10:
            st.markdown("#### Vector Similarity Matrix")
            recent_vectors = vector_dashboard.session_vectors[-20:]
            similarity_matrix = np.zeros((len(recent_vectors), len(recent_vectors)))
            
            for i in range(len(recent_vectors)):
                for j in range(len(recent_vectors)):
                    similarity_matrix[i, j] = np.dot(
                        recent_vectors[i].embedding, 
                        recent_vectors[j].embedding
                    )
            
            import plotly.graph_objects as go
            fig = go.Figure(data=go.Heatmap(
                z=similarity_matrix,
                colorscale='Viridis'
            ))
            fig.update_layout(
                title="Tick Vector Similarity (Last 20)",
                xaxis_title="Tick Index",
                yaxis_title="Tick Index"
            )
            st.plotly_chart(fig, use_container_width=True)