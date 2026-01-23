"""
Sentiment Sources - Fuentes de datos de sentimiento.

Fuentes soportadas:
- Twitter API
- Reddit API
- News APIs
"""

import logging
from typing import Any, Dict, List, Optional

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("aiohttp no disponible. Fuentes de sentimiento no funcionarán.")

from .base_source import BaseDataSource

logger = logging.getLogger(__name__)


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
        self.base_url = 'https://api.twitter.com/2'
        self.session: Optional[aiohttp.ClientSession] = None
        self._tweepy_client = None

    async def connect(self) -> bool:
        """Conectar a Twitter API."""
        if not self.bearer_token:
            logger.warning("Twitter Bearer Token no configurado. Sentiment analysis limitado.")
            # No fallar, pero limitar funcionalidad
            self.is_connected = False
            return False

        try:
            if self.use_tweepy:
                try:
                    import tweepy

                    self._tweepy_client = tweepy.Client(bearer_token=self.bearer_token)
                    self.is_connected = True
                    logger.info("Conectado a Twitter API (tweepy)")
                    return True
                except ImportError:
                    logger.warning("tweepy no disponible, usando requests directos")

            if not AIOHTTP_AVAILABLE:
                logger.error("aiohttp no disponible. TwitterSource no puede conectarse.")
                self.last_error = "aiohttp no disponible"
                return False

            self.session = aiohttp.ClientSession(
                headers={'Authorization': f'Bearer {self.bearer_token}'}
            )
            self.is_connected = True
            logger.info("Conectado a Twitter API")
            return True
        except Exception as e:
            logger.error(f"Error conectando a Twitter: {e}")
            self.last_error = str(e)
            return False

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
        except Exception as e:
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

                    avg_sentiment = (
                        sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
                    )

                    return {
                        'sentiment_score': float(avg_sentiment),
                        'positive_count': sum(1 for s in sentiment_scores if s > 0),
                        'negative_count': sum(1 for s in sentiment_scores if s < 0),
                        'neutral_count': sum(1 for s in sentiment_scores if s == 0),
                        'total_tweets': len(tweets.data),
                        'sample_tweets': sample_tweets,
                    }
                except Exception as e:
                    logger.error(f"Error usando tweepy: {e}")

            # Fallback: usar API directa (requiere implementación más compleja)
            # Por ahora retornar placeholder
            logger.warning("Twitter sentiment usando API directa no implementado completamente")
            return {'sentiment_score': 0.0, 'total_tweets': 0, 'sample_tweets': []}

        except Exception as e:
            logger.error(f"Error obteniendo sentimiento de Twitter para {symbol}: {e}")
            return {'sentiment_score': 0.0, 'total_tweets': 0, 'sample_tweets': []}


class RedditSentimentSource(BaseDataSource):
    """
    Fuente de datos de sentimiento de Reddit.

    Analiza posts y comentarios de subreddits relacionados con trading/inversiones.
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
        self.base_url = 'https://www.reddit.com'
        self.session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None

    async def connect(self) -> bool:
        """Conectar a Reddit API."""
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp no disponible. RedditSource no puede conectarse.")
            self.last_error = "aiohttp no disponible"
            return False

        try:
            self.session = aiohttp.ClientSession(headers={'User-Agent': self.user_agent})

            # Obtener access token si hay credenciales
            if self.client_id and self.client_secret:
                await self._get_access_token()

            self.is_connected = True
            logger.info("Conectado a Reddit API")
            return True
        except Exception as e:
            logger.error(f"Error conectando a Reddit: {e}")
            self.last_error = str(e)
            return False

    async def _get_access_token(self) -> None:
        """Obtener access token de Reddit."""
        try:
            auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
            async with self.session.post(
                'https://www.reddit.com/api/v1/access_token',
                auth=auth,
                data={'grant_type': 'client_credentials'},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._access_token = data.get('access_token')
                    logger.debug("Reddit access token obtenido")
        except Exception as e:
            logger.warning(f"No se pudo obtener Reddit access token: {e}")

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
        except Exception as e:
            logger.error(f"Error desconectando de Reddit: {e}")
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
        except Exception:
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
                except Exception as e:
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

            avg_sentiment = (
                sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
            )

            return {
                'sentiment_score': float(avg_sentiment),
                'positive_count': sum(1 for s in sentiment_scores if s > 0),
                'negative_count': sum(1 for s in sentiment_scores if s < 0),
                'neutral_count': sum(1 for s in sentiment_scores if s == 0),
                'total_posts': len(all_posts),
                'sample_posts': sample_posts,
            }

        except Exception as e:
            logger.error(f"Error obteniendo sentimiento de Reddit para {symbol}: {e}")
            return {'sentiment_score': 0.0, 'total_posts': 0, 'sample_posts': []}


class NewsSentimentSource(BaseDataSource):
    """
    Fuente de datos de sentimiento de noticias.

    Analiza noticias financieras para extraer sentimiento.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar fuente News Sentiment.

        Args:
            config: Configuración con:
                - api_key: News API key (opcional, puede usar múltiples servicios)
                - provider: Proveedor (newsapi, alpha_vantage, etc.)
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
        }
        return url_map.get(self.provider, url_map['newsapi'])

    async def connect(self) -> bool:
        """Conectar a News API."""
        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp no disponible. NewsSource no puede conectarse.")
            self.last_error = "aiohttp no disponible"
            return False

        try:
            self.session = aiohttp.ClientSession()
            self.is_connected = True
            logger.info(f"Conectado a News API ({self.provider})")
            return True
        except Exception as e:
            logger.error(f"Error conectando a News API: {e}")
            self.last_error = str(e)
            return False

    async def disconnect(self) -> bool:
        """Desconectar de News API."""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            self.is_connected = False
            logger.info("Desconectado de News API")
            return True
        except Exception as e:
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
            else:
                logger.warning(f"Provider {self.provider} no implementado completamente")
                return {'sentiment_score': 0.0, 'total_articles': 0, 'sample_articles': []}

        except Exception as e:
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

                avg_sentiment = (
                    sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
                )

                return {
                    'sentiment_score': float(avg_sentiment),
                    'positive_count': sum(1 for s in sentiment_scores if s > 0),
                    'negative_count': sum(1 for s in sentiment_scores if s < 0),
                    'neutral_count': sum(1 for s in sentiment_scores if s == 0),
                    'total_articles': len(articles),
                    'sample_articles': sample_articles,
                }

        except Exception as e:
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

                avg_sentiment = (
                    sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
                )

                return {
                    'sentiment_score': float(avg_sentiment),
                    'total_articles': len(feed),
                    'sample_articles': [item.get('title', '') for item in feed[:5]],
                }

        except Exception as e:
            logger.error(f"Error en Alpha Vantage News: {e}")
            return {'sentiment_score': 0.0, 'total_articles': 0}
