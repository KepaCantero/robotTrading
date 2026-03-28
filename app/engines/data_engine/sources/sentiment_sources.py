"""
Sentiment Sources - Fuentes de datos de sentimiento.

Fuentes soportadas:
- Twitter API
- Reddit API
- News APIs
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

# REQUIRED: No fallbacks - aiohttp is required for async HTTP requests
import aiohttp
import numpy as np
from requests.exceptions import HTTPError, RequestException
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)

from app.shared.config.api_endpoints import APIEndpoints
from app.shared.config.timeout_config import get_timeouts

from .base_source import BaseDataSource

# Optional tweepy import for Twitter sentiment analysis
try:
    import tweepy

    TWEEPY_AVAILABLE = True
except ImportError:
    tweepy = None
    TWEEPY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Get centralized timeouts
_TIMEOUTS = get_timeouts()


class TwitterSentimentSource(BaseDataSource):
    """
    Fuente de datos de sentimiento de Twitter/X.

    Analiza tweets relacionados con símbolos para extraer sentimiento.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente Twitter Sentiment.

        Args:
            config: Configuración con:
                - bearer_token: Twitter API Bearer Token
                - use_tweepy: Usar tweepy library (opcional)
        """
        super().__init__(config)
        self.bearer_token = config.get('bearer_token')
        self.use_tweepy = config.get('use_tweepy', False)
        # Use centralized endpoint configuration
        self.base_url = config.get('base_url', APIEndpoints.TWITTER_API)
        self.session: Optional[aiohttp.ClientSession] = None
        self._tweepy_client = None

    async def connect(self) -> bool:
        """Conectar a Twitter API."""
        if not self.bearer_token:
            logger.warning("Twitter Bearer Token no configurado. Sentiment analysis limitado.")
            # No fallar, pero limitar funcionalidad
            self.is_connected = False
            return False

        # Initialize tweepy client if available and requested
        if self.use_tweepy and TWEEPY_AVAILABLE and tweepy is not None:
            try:
                self._tweepy_client = tweepy.Client(bearer_token=self.bearer_token)
                self.is_connected = True
                logger.info("Conectado a Twitter API usando tweepy")
                return True
            except Exception as e:
                logger.error(f"Error inicializando tweepy: {e}")
                self._tweepy_client = None

        self.is_connected = True
        return True

    async def disconnect(self) -> bool:
        """Desconectar de Twitter."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self._tweepy_client = None
            self.is_connected = False
            logger.info("Desconectado de Twitter")
            return True
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.error(f"Error desconectando de Twitter: {e}")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected:
            return False
        # Twitter API v2 no tiene endpoint de health simple
        return True

    async def get_sentiment(
        self, symbol: str, query: Optional[str] = None, max_results: int = 100
    ) -> Dict[str, Any]:
        """
        Obtener sentimiento de Twitter para un símbolo.

        Args:
            symbol: Símbolo del ticker
            query: Query personalizado (opcional, usa symbol si no se proporciona)
            max_results: Número máximo de tweets a analizar

        Returns:
            Dict con:
                - sentiment_score: float (-1 a 1)
                - positive_count: int
                - negative_count: int
                - neutral_count: int
                - total_tweets: int
                - sample_tweets: List[str]
        """
        if not self.is_connected:
            logger.warning("No conectado a Twitter API")
            return {
                'sentiment_score': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'total_tweets': 0,
                'sample_tweets': [],
            }

        try:
            # Construir query
            search_query = query or f"${symbol} OR {symbol}"

            # Usar tweepy si está disponible
            if self._tweepy_client:
                try:
                    tweets = self._tweepy_client.search_recent_tweets(
                        query=search_query,
                        max_results=min(max_results, 100),  # Twitter limita a 100
                        tweet_fields=['text', 'created_at', 'public_metrics'],
                    )

                    if not tweets.data:
                        return {'sentiment_score': 0.0, 'total_tweets': 0, 'sample_tweets': []}

                    # Analizar sentimiento (simplificado - en producción usar NLP)
                    sentiment_scores = []
                    sample_tweets = []

                    for tweet in tweets.data[:10]:  # Sample de primeros 10
                        sample_tweets.append(tweet.text)
                        # Sentimiento simple basado en palabras clave
                        text_lower = tweet.text.lower()
                        if any(
                            word in text_lower
                            for word in ['bull', 'buy', 'up', 'moon', 'rocket', 'profit']
                        ):
                            sentiment_scores.append(0.5)
                        elif any(
                            word in text_lower
                            for word in ['bear', 'sell', 'down', 'crash', 'loss', 'dump']
                        ):
                            sentiment_scores.append(-0.5)
                        else:
                            sentiment_scores.append(0.0)

                    avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.0

                    return {
                        'sentiment_score': float(avg_sentiment),
                        'positive_count': sum(1 for s in sentiment_scores if s > 0),
                        'negative_count': sum(1 for s in sentiment_scores if s < 0),
                        'neutral_count': sum(1 for s in sentiment_scores if s == 0),
                        'total_tweets': len(tweets.data),
                        'sample_tweets': sample_tweets,
                    }
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    logger.error(f"Error usando tweepy: {e}")

            # Fallback: usar API directa (requiere implementación más compleja)
            # Por ahora retornar placeholder
            logger.warning("Twitter sentiment usando API directa no implementado completamente")
            return {'sentiment_score': 0.0, 'total_tweets': 0, 'sample_tweets': []}

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error obteniendo sentimiento de Twitter para {symbol}: {e}")
            return {'sentiment_score': 0.0, 'total_tweets': 0, 'sample_tweets': []}


class RedditSentimentSource(BaseDataSource):
    """
    Fuente de datos de sentimiento de Reddit.

    Analiza posts y comentarios de subreddits relacionados con trading/inversiones.
    Uses centralized endpoint configuration.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente Reddit Sentiment.

        Args:
            config: Configuración con:
                - client_id: Reddit API client ID (opcional)
                - client_secret: Reddit API client secret (opcional)
                - user_agent: User agent string
        """
        super().__init__(config)
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.user_agent = config.get('user_agent', 'algoTrading/1.0')
        # Use centralized endpoint configuration
        self._timeouts = get_timeouts()
        self.base_url = config.get('base_url', APIEndpoints.REDDIT_API)
        self.token_url = config.get('token_url', APIEndpoints.REDDIT_TOKEN)
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None

    async def connect(self) -> bool:
        """Conectar a Reddit API."""
        try:
            self.session = aiohttp.ClientSession(headers={'User-Agent': self.user_agent})

            # Obtener access token si hay credenciales
            if self.client_id and self.client_secret:
                await self._get_access_token()

            self.is_connected = True
            logger.info("Conectado a Reddit API")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a Reddit: {e}")
            self.last_error = str(e)
            raise

    async def _get_access_token(self) -> None:
        """Obtener access token de Reddit using centralized endpoint."""
        try:
            auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
            async with self.session.post(
                self.token_url,  # Use centralized endpoint
                auth=auth,
                data={'grant_type': 'client_credentials'},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._access_token = data.get('access_token')
                    logger.debug("Reddit access token obtenido")
        except (asyncio.TimeoutError, OSError):
            # Don't log exception details at warning level - could contain sensitive data
            logger.warning("Failed to obtain Reddit access token")

    async def disconnect(self) -> bool:
        """Desconectar de Reddit."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self._access_token = None
            self.is_connected = False
            logger.info("Desconectado de Reddit")
            return True
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError):
            # Don't log exception details - could contain sensitive data
            logger.error("Error disconnecting from Reddit")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected or not self.session:
            return False
        try:
            # Test con subreddit público
            async with self.session.get(
                f"{self.base_url}/r/wallstreetbets/hot.json?limit=1"
            ) as response:
                return response.status == 200
        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError):
            return False

    async def get_sentiment(
        self, symbol: str, subreddits: List[str] = None, max_posts: int = 50
    ) -> Dict[str, Any]:
        """
        Obtener sentimiento de Reddit para un símbolo.

        Args:
            symbol: Símbolo del ticker
            subreddits: Lista de subreddits a buscar (default: ['wallstreetbets', 'stocks', 'investing'])
            max_posts: Número máximo de posts a analizar

        Returns:
            Dict con sentimiento
        """
        if not self.is_connected or not self.session:
            logger.warning("No conectado a Reddit API")
            return {'sentiment_score': 0.0, 'total_posts': 0, 'sample_posts': []}

        if subreddits is None:
            subreddits = ['wallstreetbets', 'stocks', 'investing']

        try:
            all_posts = []

            for subreddit in subreddits:
                try:
                    url = f"{self.base_url}/r/{subreddit}/search.json"
                    params = {
                        'q': symbol,
                        'limit': min(max_posts, 25),  # Reddit limita a 25 por request
                        'sort': 'relevance',
                    }

                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'data' in data and 'children' in data['data']:
                                for post in data['data']['children']:
                                    post_data = post.get('data', {})
                                    all_posts.append(
                                        {
                                            'title': post_data.get('title', ''),
                                            'text': post_data.get('selftext', ''),
                                            'score': post_data.get('score', 0),
                                            'created_utc': post_data.get('created_utc', 0),
                                        }
                                    )
                except (asyncio.TimeoutError, OSError) as e:
                    logger.warning(f"Error buscando en r/{subreddit}: {e}")
                    continue

            if not all_posts:
                return {'sentiment_score': 0.0, 'total_posts': 0, 'sample_posts': []}

            # Analizar sentimiento (simplificado)
            sentiment_scores = []
            sample_posts = []

            for post in all_posts[:10]:  # Sample de primeros 10
                text = f"{post['title']} {post['text']}".lower()
                sample_posts.append(post['title'])

                # Sentimiento simple
                if any(
                    word in text
                    for word in ['bull', 'buy', 'up', 'moon', 'rocket', 'profit', 'gain']
                ):
                    sentiment_scores.append(0.5)
                elif any(
                    word in text
                    for word in ['bear', 'sell', 'down', 'crash', 'loss', 'dump', 'drop']
                ):
                    sentiment_scores.append(-0.5)
                else:
                    sentiment_scores.append(0.0)

            avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.0

            return {
                'sentiment_score': float(avg_sentiment),
                'positive_count': sum(1 for s in sentiment_scores if s > 0),
                'negative_count': sum(1 for s in sentiment_scores if s < 0),
                'neutral_count': sum(1 for s in sentiment_scores if s == 0),
                'total_posts': len(all_posts),
                'sample_posts': sample_posts,
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error obteniendo sentimiento de Reddit para {symbol}: {e}")
            return {'sentiment_score': 0.0, 'total_posts': 0, 'sample_posts': []}


class NewsSentimentSource(BaseDataSource):
    """
    Fuente de datos de sentimiento de noticias.

    Analiza noticias financieras para extraer sentimiento.
    Soporta múltiples proveedores: NewsAPI, Alpha Vantage, Marketaux.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente News Sentiment.

        Args:
            config: Configuración con:
                - api_key: News API key (opcional, puede usar múltiples servicios)
                - provider: Proveedor (newsapi, alpha_vantage, marketaux)
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.provider = config.get('provider', 'newsapi')
        self.base_url = self._get_base_url()
        self.session: Optional[aiohttp.ClientSession] = None

    def _get_base_url(self) -> str:
        """Obtener base URL según provider."""
        url_map = {
            'newsapi': 'https://newsapi.org/v2',
            'alpha_vantage': 'https://www.alphavantage.co/query',
            'marketaux': 'https://api.marketaux.com/v1',
        }
        return url_map.get(self.provider, url_map['newsapi'])

    async def connect(self) -> bool:
        """Conectar a News API."""
        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            logger.info(f"Conectado a News API ({self.provider})")
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Error conectando a News API: {e}")
            self.last_error = str(e)
            raise

    async def disconnect(self) -> bool:
        """Desconectar de News API."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.is_connected = False
            logger.info("Desconectado de News API")
            return True
        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error desconectando de News API: {e}")
            return False

    async def health_check(self) -> bool:
        """Verificar salud de la conexión."""
        if not self.is_connected or not self.session:
            return False
        return True  # News APIs generalmente no tienen health check simple

    async def get_sentiment(self, symbol: str, max_articles: int = 50) -> Dict[str, Any]:
        """
        Obtener sentimiento de noticias para un símbolo.

        Args:
            symbol: Símbolo del ticker
            max_articles: Número máximo de artículos a analizar

        Returns:
            Dict con sentimiento
        """
        if not self.is_connected or not self.session:
            logger.warning("No conectado a News API")
            return {'sentiment_score': 0.0, 'total_articles': 0, 'sample_articles': []}

        try:
            if self.provider == 'newsapi':
                return await self._get_newsapi_sentiment(symbol, max_articles)
            elif self.provider == 'alpha_vantage':
                return await self._get_alphavantage_news_sentiment(symbol)
            elif self.provider == 'marketaux':
                return await self._get_marketaux_sentiment(symbol, max_articles)
            else:
                logger.warning(f"Provider {self.provider} no implementado completamente")
                return {'sentiment_score': 0.0, 'total_articles': 0, 'sample_articles': []}

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error obteniendo sentimiento de noticias para {symbol}: {e}")
            return {'sentiment_score': 0.0, 'total_articles': 0, 'sample_articles': []}

    async def _get_newsapi_sentiment(self, symbol: str, max_articles: int) -> Dict[str, Any]:
        """Obtener sentimiento usando NewsAPI."""
        if not self.api_key:
            logger.warning("NewsAPI key no configurado")
            return {'sentiment_score': 0.0, 'total_articles': 0}

        try:
            url = f"{self.base_url}/everything"
            params = {
                'q': symbol,
                'apiKey': self.api_key,
                'pageSize': min(max_articles, 100),
                'sortBy': 'relevancy',
                'language': 'en',
            }

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"NewsAPI error: {response.status}")
                    return {'sentiment_score': 0.0, 'total_articles': 0}

                data = await response.json()
                articles = data.get('articles', [])

                if not articles:
                    return {'sentiment_score': 0.0, 'total_articles': 0}

                # Analizar sentimiento
                sentiment_scores = []
                sample_articles = []

                for article in articles[:10]:
                    title = article.get('title', '')
                    description = article.get('description', '')
                    text = f"{title} {description}".lower()
                    sample_articles.append(title)

                    # Sentimiento simple
                    if any(
                        word in text
                        for word in ['bull', 'buy', 'up', 'gain', 'profit', 'growth', 'positive']
                    ):
                        sentiment_scores.append(0.5)
                    elif any(
                        word in text
                        for word in ['bear', 'sell', 'down', 'loss', 'decline', 'negative', 'drop']
                    ):
                        sentiment_scores.append(-0.5)
                    else:
                        sentiment_scores.append(0.0)

                avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.0

                return {
                    'sentiment_score': float(avg_sentiment),
                    'positive_count': sum(1 for s in sentiment_scores if s > 0),
                    'negative_count': sum(1 for s in sentiment_scores if s < 0),
                    'neutral_count': sum(1 for s in sentiment_scores if s == 0),
                    'total_articles': len(articles),
                    'sample_articles': sample_articles,
                }

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error en NewsAPI: {e}")
            return {'sentiment_score': 0.0, 'total_articles': 0}

    async def _get_alphavantage_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Obtener sentimiento usando Alpha Vantage News & Sentiment API."""
        if not self.api_key:
            logger.warning("Alpha Vantage API key no configurado")
            return {'sentiment_score': 0.0, 'total_articles': 0}

        try:
            params = {'function': 'NEWS_SENTIMENT', 'tickers': symbol, 'apikey': self.api_key}

            async with self.session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    return {'sentiment_score': 0.0, 'total_articles': 0}

                data = await response.json()

                if 'Error Message' in data or 'Note' in data:
                    logger.warning(
                        f"Alpha Vantage error: {data.get('Error Message', data.get('Note'))}"
                    )
                    return {'sentiment_score': 0.0, 'total_articles': 0}

                feed = data.get('feed', [])

                if not feed:
                    return {'sentiment_score': 0.0, 'total_articles': 0}

                # Alpha Vantage ya proporciona sentiment scores
                sentiment_scores = []
                for item in feed:
                    ticker_sentiment = item.get('ticker_sentiment', [])
                    for ticker in ticker_sentiment:
                        if ticker.get('ticker') == symbol:
                            relevance = float(ticker.get('relevance_score', 0))
                            sentiment = float(ticker.get('ticker_sentiment_score', 0))
                            # Ponderar por relevancia
                            sentiment_scores.append(sentiment * relevance)

                avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.0

                return {
                    'sentiment_score': float(avg_sentiment),
                    'total_articles': len(feed),
                    'sample_articles': [item.get('title', '') for item in feed[:5]],
                }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en Alpha Vantage News: {e}")
            return {'sentiment_score': 0.0, 'total_articles': 0}

    async def _get_marketaux_sentiment(self, symbol: str, max_articles: int = 50) -> Dict[str, Any]:
        """
        Obtener sentimiento usando Marketaux API.

        Marketaux proporciona:
        - News con sentiment score (-1 a +1) pre-calculado
        - Entity identification con match scores
        - Soporte para equity, cryptocurrency, forex, indices
        - Multi-idioma (incluyendo español para España)
        - Filtros por país, industria, entity type

        Args:
            symbol: Símbolo del ticker (ej: AAPL, BTCUSD, EURUSD)
            max_articles: Número máximo de artículos

        Returns:
            Dict con:
                - sentiment_score: float (-1 a 1)
                - positive_count: int
                - negative_count: int
                - neutral_count: int
                - total_articles: int
                - sample_articles: List[str]
                - entities: List[Dict] con entity details
        """
        if not self.api_key:
            logger.warning("Marketaux API key no configurada")
            return {'sentiment_score': 0.0, 'total_articles': 0, 'sample_articles': []}

        try:
            url = f"{self.base_url}/news/all"
            params = {
                'api_token': self.api_key,
                'symbols': symbol,
                'filter_entities': 'true',  # Solo entidades relevantes
                'must_have_entities': 'true',  # Artículos con entidades identificadas
                'language': 'en,es',  # Inglés y Español
                'limit': min(max_articles, 100),
                'sort': 'published_at',
            }

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    logger.error(f"Marketaux API error: {response.status}")
                    return {'sentiment_score': 0.0, 'total_articles': 0, 'sample_articles': []}

                data = await response.json()

                # Manejar errores de API
                if 'error' in data:
                    logger.error(f"Marketaux error: {data['error']}")
                    return {'sentiment_score': 0.0, 'total_articles': 0, 'sample_articles': []}

                articles = data.get('data', [])
                meta = data.get('meta', {})

                if not articles:
                    logger.debug(f"No articles found for {symbol}")
                    return {
                        'sentiment_score': 0.0,
                        'total_articles': 0,
                        'found': meta.get('found', 0),
                        'sample_articles': [],
                    }

                # Marketaux YA proporciona sentiment scores pre-calculados
                # No necesitamos calcularlos nosotros
                sentiment_scores = []
                sample_articles = []
                all_entities = []

                positive_count = 0
                negative_count = 0
                neutral_count = 0

                for article in articles:
                    title = article.get('title', '')
                    article.get('snippet', '')
                    published_at = article.get('published_at', '')
                    source = article.get('source', '')

                    sample_articles.append(f"{title} ({source})")

                    # Extraer entities y sus sentiment scores
                    entities = article.get('entities', [])

                    for entity in entities:
                        entity_symbol = entity.get('symbol', '')
                        entity_name = entity.get('name', '')
                        sentiment_score = entity.get('sentiment_score', 0.0)
                        match_score = entity.get('match_score', 0.0)

                        # Solo considerar la entidad que buscamos
                        if entity_symbol == symbol:
                            # Ponderar por match score (relevancia)
                            weighted_sentiment = sentiment_score * (min(match_score, 100) / 100)
                            sentiment_scores.append(weighted_sentiment)

                            all_entities.append(
                                {
                                    'symbol': entity_symbol,
                                    'name': entity_name,
                                    'sentiment': sentiment_score,
                                    'match_score': match_score,
                                    'published_at': published_at,
                                }
                            )

                            # Contar positivos/negativos/neutrales
                            if sentiment_score > 0.1:
                                positive_count += 1
                            elif sentiment_score < -0.1:
                                negative_count += 1
                            else:
                                neutral_count += 1

                # Calcular sentimiento promedio ponderado
                if sentiment_scores:
                    avg_sentiment = np.mean(sentiment_scores)
                else:
                    avg_sentiment = 0.0

                result = {
                    'sentiment_score': float(avg_sentiment),
                    'positive_count': positive_count,
                    'negative_count': negative_count,
                    'neutral_count': neutral_count,
                    'total_articles': len(articles),
                    'total_entities': len(all_entities),
                    'sample_articles': sample_articles[:5],  # Máximo 5 samples
                    'entities': all_entities[:10],  # Máximo 10 entities
                    'found_total': meta.get('found', 0),
                }

                logger.info(
                    f"Marketaux sentiment for {symbol}: {avg_sentiment:.3f} "
                    f"({len(articles)} articles, {len(all_entities)} entities)"
                )

                return result

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error en Marketaux API para {symbol}: {e}")
            return {'sentiment_score': 0.0, 'total_articles': 0, 'sample_articles': []}
