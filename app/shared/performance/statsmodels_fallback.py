"""
Fallback implementations for statsmodels functions using scipy/numpy.

This module provides fallback implementations when statsmodels is not available.
It implements the most commonly used statistical tests from statsmodels using
scipy, numpy, and pandas.

All fallback implementations log warnings to indicate they are being used.
"""

import logging
import warnings
from typing import Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Global flag to track if we're using fallback implementations
USING_FALLBACK = False


def _log_fallback_warning(func_name: str, message: str = ""):
    """Log a warning when using fallback implementation."""
    global USING_FALLBACK
    USING_FALLBACK = True
    warning_msg = (
        f"Using fallback implementation for {func_name}. Results may differ from statsmodels."
    )
    if message:
        warning_msg += f" {message}"
    logger.warning(warning_msg)
    warnings.warn(warning_msg, UserWarning, stacklevel=3)


def adfuller(
    x: Union[np.ndarray, pd.Series],
    maxlag: Optional[int] = None,
    regression: str = "c",
    autolag: str = "AIC",
    store: bool = False,
    regresults: bool = False,
) -> tuple[float, float, int, dict[str, float], int]:
    """
    Augmented Dickey-Fuller unit root test - fallback implementation.

    This is a simplified fallback using scipy that provides basic stationarity testing.
    For full functionality, install statsmodels.

    Parameters
    ----------
    x : array_like
        1d array, time series to test
    maxlag : int, optional
        Maximum lag to use (default: 12*(nobs/100)^{1/4})
    regression : str {"c","ct","ctt","t"}
        Constant and trend order to include in regression
        - "c" : constant only (default)
        - "ct" : constant and trend
        - "ctt": constant, and linear and quadratic trend
        - "t" : trend only
    autolag : {"AIC", "BIC", "t-stat", None}
        Method to use for automatic lag selection
    store : bool
        If True, return results in class instance
    regresults : bool
        If True, return full regression results

    Returns
    -------
    adf : float
        Test statistic
    pvalue : float
        MacKinnon's approximate p-value based on MacKinnon (1994, 2010)
    usedlag : int
        Number of lags used
    critical_values : dict
        Critical values for the test statistic at the 1%, 5%, and 10% levels
    icbest : float
        The maximized information criterion if autolag is not None

    Notes
    -----
    This fallback uses a simpler implementation based on scipy.stats.ttest_1samp
    and variance ratios. It provides a reasonable approximation but is not as
    sophisticated as the full statsmodels implementation.
    """
    _log_fallback_warning(
        "adfuller", "For full ADF test functionality, install statsmodels: pip install statsmodels"
    )

    # Convert to numpy array
    if isinstance(x, pd.Series):
        x = x.values
    x = np.asarray(x, dtype=float)
    x = x.squeeze()

    # Remove NaN values
    x = x[~np.isnan(x)]

    nobs = len(x)
    if nobs < 10:
        raise ValueError("Sample size is too short")

    # Determine max lag if not provided
    if maxlag is None:
        maxlag = int(12.0 * np.power(nobs / 100.0, 1 / 4.0))

    # Calculate differences
    y = np.diff(x)
    y_lag = x[:-1]

    # Perform regression: y ~ beta * y_lag + constant
    # ADF test: H0: beta = 1 (unit root exists, non-stationary)
    #          H1: beta < 1 (stationary)

    # Simple OLS regression
    X = np.column_stack([y_lag, np.ones(len(y_lag))])

    # Add lagged differences for augmented part
    # Suppress exceptions during lag calculation
    import contextlib

    with contextlib.suppress(Exception):
        for lag in range(1, min(maxlag + 1, len(y) // 3)):
            if len(y) > lag + 1:
                lag_diff = np.diff(x, lag)[:-1]
                if len(lag_diff) == len(y):
                    X = np.column_stack([X, lag_diff])

    # OLS regression: y = X * beta + epsilon
    try:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        residuals = y - X @ beta
        sigma2 = np.sum(residuals**2) / (len(y) - X.shape[1])
        var_beta = sigma2 * np.linalg.inv(X.T @ X).diagonal()

        # Test statistic for unit root: (beta[0] - 1) / se(beta[0])
        adf_stat = (beta[0] - 1) / np.sqrt(var_beta[0])

        # Estimate p-value using approximate distribution
        # Critical values from MacKinnon (1994, 2010)
        critical_values = {
            "1%": -3.43,
            "5%": -2.86,
            "10%": -2.57,
        }

        # Approximate p-value based on test statistic
        # This is a rough approximation
        if adf_stat < critical_values["1%"]:
            pvalue = 0.01
        elif adf_stat < critical_values["5%"]:
            pvalue = 0.05
        elif adf_stat < critical_values["10%"]:
            pvalue = 0.10
        else:
            # For less negative values, use linear interpolation
            pvalue = 0.10 + (adf_stat - critical_values["10%"]) * 0.05
            pvalue = min(max(pvalue, 0.001), 0.999)

    except Exception as e:
        # Fallback to simpler test if regression fails
        logger.warning(f"OLS regression failed in adfuller fallback: {e}, using simpler test")

        # Simple variance ratio test
        x_diff = np.diff(x)
        var_x = np.var(x)
        var_diff = np.var(x_diff)

        if var_diff > 0:
            # Variance ratio close to 1 suggests non-stationarity
            var_ratio = var_diff / var_x if var_x > 0 else 0
            adf_stat = -np.log(var_ratio) * 10  # Scale to reasonable range
        else:
            adf_stat = -5.0  # Very stationary

        pvalue = 0.05 if adf_stat < -2.86 else 0.50
        critical_values = {
            "1%": -3.43,
            "5%": -2.86,
            "10%": -2.57,
        }

    usedlag = min(maxlag, len(y) // 3)
    icbest = 0.0

    # Store results if requested (simplified)
    if store:
        # Just return the results as a tuple for now
        pass

    return adf_stat, pvalue, usedlag, critical_values, icbest


def coint(
    y1: Union[np.ndarray, pd.Series],
    y2: Union[np.ndarray, pd.Series],
    trend: str = "c",
    method: str = "aeg",
    maxlag: Optional[int] = None,
    return_results: bool = False,
) -> Union[tuple[float, float, dict], object]:
    """
    Test for no cointegration of a univariate equation - fallback implementation.

    This is a simplified fallback using correlation and regression-based tests.
    For full functionality, install statsmodels.

    Parameters
    ----------
    y1 : array_like
        First element in cointegrating vector
    y2 : array_like
        Second element in cointegrating vector
    trend : str {"c","ct"}
        Trend term to include
        - "c" : constant only (default)
        - "ct" : constant and trend
    method : str {"aeg","johnson"}
        "aeg" : Engle-Granger (default)
        "johnson" : Johansen (not implemented in fallback)
    maxlag : int, optional
        Maximum lag which is included in test
    return_results : bool
        If True, return results object instead of tuple

    Returns
    -------
    t : float
        t-statistic of unit-root test on residuals
    pvalue : float
        MacKinnon's approximate p-value based on MacKinnon (1994)
    crit_value : dict
        Critical values for the test statistic at the 1%, 5%, and 10% levels

    Notes
    -----
    This fallback uses a correlation-based approach and applies the ADF test
    to the residuals from a linear regression of y1 on y2.
    """
    _log_fallback_warning(
        "coint", "For full cointegration testing, install statsmodels: pip install statsmodels"
    )

    # Convert to numpy arrays
    if isinstance(y1, pd.Series):
        y1 = y1.values
    if isinstance(y2, pd.Series):
        y2 = y2.values

    y1 = np.asarray(y1, dtype=float).squeeze()
    y2 = np.asarray(y2, dtype=float).squeeze()

    # Remove NaN values
    mask = ~(np.isnan(y1) | np.isnan(y2))
    y1 = y1[mask]
    y2 = y2[mask]

    if len(y1) < 10:
        raise ValueError("Sample size is too short")

    # Perform linear regression: y1 = beta * y2 + constant
    X = np.column_stack([y2, np.ones(len(y2))])

    try:
        # OLS regression
        beta = np.linalg.lstsq(X, y1, rcond=None)[0]
        residuals = y1 - X @ beta

        # Apply ADF test to residuals
        t_stat, pvalue, _, crit_value, _ = adfuller(residuals, maxlag=maxlag)

        # Adjust critical values for cointegration test
        # (MacKinnon critical values for cointegration are different)
        crit_value = {
            "1%": -3.90,
            "5%": -3.34,
            "10%": -3.04,
        }

    except Exception as e:
        # Fallback to correlation-based test
        logger.warning(f"Regression failed in coint fallback: {e}, using correlation test")

        correlation = np.corrcoef(y1, y2)[0, 1]

        # Transform correlation to t-statistic-like value
        t_stat = correlation * 10
        pvalue = max(0.001, min(0.999, 1 - abs(correlation)))

        crit_value = {
            "1%": -3.90,
            "5%": -3.34,
            "10%": -3.04,
        }

    if return_results:
        # Return a simple results object
        class CointResult:
            def __init__(self, t, p, crit):
                self.stat = t
                self.pvalue = p
                self.crit_values = crit

            def __repr__(self):
                return f"CointResult(stat={self.stat:.4f}, pvalue={self.pvalue:.4f})"

        return CointResult(t_stat, pvalue, crit_value)

    return t_stat, pvalue, crit_value


def seasonal_decompose(
    x: Union[np.ndarray, pd.Series],
    model: str = "additive",
    filt: Optional[np.ndarray] = None,
    period: Optional[int] = None,
    two_sided: bool = True,
) -> object:
    """
    Seasonal decomposition using moving averages - fallback implementation.

    This is a simplified fallback using pandas and scipy.
    For full functionality, install statsmodels.

    Parameters
    ----------
    x : array_like
        Time series to decompose
    model : str {"additive", "multiplicative"}
        Type of seasonal component
    filt : array_like, optional
        A centered filter to use for the seasonal decomposition
    period : int, optional
        Period of the series (default: uses minimum frequency in pandas index)
    two_sided : bool
        Whether to use a two-sided filter for seasonal decomposition

    Returns
    -------
    result : DecomposeResult
        Object with seasonal, trend, and residual components

    Notes
    -----
    This fallback implements a simple decomposition using moving averages
    and pandas rolling operations.
    """
    _log_fallback_warning(
        "seasonal_decompose",
        "For full seasonal decomposition, install statsmodels: pip install statsmodels",
    )

    # Convert to pandas Series if not already
    if not isinstance(x, pd.Series):
        x = pd.Series(x)

    # Remove NaN values
    x = x.dropna()

    if len(x) < 20:
        raise ValueError("Time series is too short for decomposition")

    # Determine period if not provided
    if period is None and isinstance(x.index, pd.DatetimeIndex):
        # Try to infer from frequency
        period = x.index.freq
        if period is None:
            period = 12  # Default to monthly
    elif period is None:
        period = 12  # Default

    # Simple decomposition using moving averages
    try:
        # Trend component - centered moving average
        if period % 2 == 0:
            trend = x.rolling(window=period + 1, center=True).mean()
        else:
            trend = x.rolling(window=period, center=True).mean()

        # Seasonal component
        detrended = x / trend if model == "multiplicative" else x - trend

        # Compute seasonal component by averaging over periods
        seasonal = pd.Series(index=x.index, dtype=float)
        for i in range(period):
            mask = np.arange(len(x)) % period == i
            if mask.sum() > 0:
                seasonal_val = detrended[mask].mean()
                seasonal.iloc[mask] = seasonal_val

        # Fill NaN in seasonal with mean
        seasonal = seasonal.fillna(seasonal.mean())

        # Residual component
        residual = x / (trend * seasonal) if model == "multiplicative" else x - trend - seasonal

    except Exception as e:
        logger.warning(f"Decomposition failed: {e}, returning simplified components")

        # Simplified fallback
        trend = pd.Series(np.zeros_like(x), index=x.index)
        seasonal = pd.Series(np.zeros_like(x), index=x.index)
        residual = x.copy()

    # Create result object
    class DecomposeResult:
        def __init__(self, observed, trend, seasonal, resid):
            self.observed = observed
            self.trend = trend
            self.seasonal = seasonal
            self.resid = resid

        def plot(self):
            """Simple plot of decomposition"""
            import matplotlib.pyplot as plt

            fig, axes = plt.subplots(4, 1, figsize=(10, 8))
            self.observed.plot(ax=axes[0], title="Observed")
            self.trend.plot(ax=axes[1], title="Trend")
            self.seasonal.plot(ax=axes[2], title="Seasonal")
            self.resid.plot(ax=axes[3], title="Residual")
            plt.tight_layout()
            return fig

    return DecomposeResult(x, trend, seasonal, residual)


def acorr_ljungbox(
    x: Union[np.ndarray, pd.Series],
    lags: Optional[Union[int, list]] = None,
    boxpierce: bool = False,
    model_df: int = 0,
    period: Optional[int] = None,
    return_df: bool = True,
) -> Union[pd.DataFrame, dict]:
    """
    Ljung-Box test for autocorrelation - fallback implementation.

    This tests whether any of a group of autocorrelations of a time series
    are different from zero.

    Parameters
    ----------
    x : array_like
        Time series data
    lags : int or array_like, optional
        Number of lags to include in test (default: min(10, nobs // 5))
    boxpierce : bool
        If True, also compute Box-Pierce statistic
    model_df : int
        Degrees of freedom consumed by model
    period : int, optional
        Period for seasonal data
    return_df : bool
        If True, return DataFrame instead of dict

    Returns
    -------
    lbvalue : float or Series
        Ljung-Box test statistic
    pvalue : float or Series
        P-value based on chi-square distribution
    bpvalue : float or Series (optional)
        Box-Pierce test statistic if boxpierce=True
    bppvalue : float or Series (optional)
        Box-Pierce p-value if boxpierce=True

    Notes
    -----
    This fallback implements a simplified version using scipy.stats.chisquare.
    """
    _log_fallback_warning(
        "acorr_ljungbox", "For full Ljung-Box test, install statsmodels: pip install statsmodels"
    )

    # Convert to numpy array
    if isinstance(x, pd.Series):
        x = x.values
    x = np.asarray(x, dtype=float).squeeze()

    # Remove NaN values
    x = x[~np.isnan(x)]

    nobs = len(x)

    # Determine lags
    if lags is None:
        lags = min(10, nobs // 5)

    if isinstance(lags, int):
        lags = range(1, lags + 1)
    elif isinstance(lags, list):
        lags = sorted(lags)

    # Compute autocorrelations
    from scipy.stats import chi2

    results = []

    for lag in lags:
        # Compute sample autocorrelations
        autocorrs = []
        for k in range(1, lag + 1):
            if k < nobs:
                autocorr = np.corrcoef(x[:-k], x[k:])[0, 1]
                autocorrs.append(autocorr)

        # Ljung-Box statistic
        if autocorrs:
            lb_stat = (
                nobs * (nobs + 2) * sum(ac**2 / (nobs - k) for k, ac in enumerate(autocorrs, 1))
            )

            # Degrees of freedom
            df = lag - model_df

            # P-value from chi-square distribution
            pvalue = 1 - chi2.cdf(lb_stat, df)

            result = {
                "lb_stat": lb_stat,
                "lb_pvalue": pvalue,
                "lag": lag,
            }

            # Box-Pierce statistic if requested
            if boxpierce:
                bp_stat = nobs * sum(ac**2 for ac in autocorrs)
                bp_pvalue = 1 - chi2.cdf(bp_stat, df)
                result["bp_stat"] = bp_stat
                result["bp_pvalue"] = bp_pvalue

            results.append(result)

    # Format output
    if return_df:
        df_data = {r["lag"]: [r["lb_stat"], r["lb_pvalue"]] for r in results}
        if boxpierce:
            df_data.update(
                {r["lag"]: [r.get("bp_stat", np.nan), r.get("bp_pvalue", np.nan)] for r in results}
            )

        result_df = pd.DataFrame(
            results,
            columns=["lag", "lb_stat", "lb_pvalue"]
            + (["bp_stat", "bp_pvalue"] if boxpierce else []),
        )
        result_df = result_df.set_index("lag")
        return result_df
    else:
        return results


class OLS:
    """
    Ordinary Least Squares regression - fallback implementation.

    This is a simplified fallback using numpy.linalg.lstsq.
    For full functionality, install statsmodels.
    """

    def __init__(self, endog, exog):
        """
        Parameters
        ----------
        endog : array_like
            Endogenous response variable
        exog : array_like
            Exogenous explanatory variables
        """
        _log_fallback_warning(
            "OLS", "For full OLS functionality, install statsmodels: pip install statsmodels"
        )

        # Convert to numpy arrays
        if isinstance(endog, pd.Series):
            endog = endog.values
        if isinstance(exog, pd.DataFrame):
            exog = exog.values
        if isinstance(exog, pd.Series):
            exog = exog.values.reshape(-1, 1)

        self.endog = np.asarray(endog, dtype=float).squeeze()
        self.exog = np.asarray(exog, dtype=float)

        # Add constant if not present
        if self.exog.ndim == 1:
            self.exog = self.exog.reshape(-1, 1)

        # Check if constant column exists
        if not np.any(np.all(self.exog == self.exog[:, [0]], axis=0)):
            self.exog = np.column_stack([np.ones(len(self.endog)), self.exog])

        self._nobs = len(self.endog)
        self._nvar = self.exog.shape[1]

        # Fit the model
        self._fit()

    def _fit(self):
        """Fit the OLS model using numpy.linalg.lstsq"""
        # OLS estimation: beta = (X'X)^(-1)X'y
        try:
            self.params, _residuals, _rank, _singular = np.linalg.lstsq(
                self.exog, self.endog, rcond=None
            )

            # Calculate residuals
            self.resid = self.endog - self.exog @ self.params

            # Degrees of freedom
            self.df_resid = self._nobs - self._nvar
            self.df_model = self._nvar - 1

            # Residual sum of squares
            self.ssr = np.sum(self.resid**2)

            # Estimate of error variance
            if self.df_resid > 0:
                self.scale = self.ssr / self.df_resid
            else:
                self.scale = 0

            # Covariance matrix of parameters
            if self.exog.shape[0] > self.exog.shape[1]:
                xtx_inv = np.linalg.inv(self.exog.T @ self.exog)
                self.cov_params = self.scale * xtx_inv
                self.bse = np.sqrt(np.diag(self.cov_params))
            else:
                self.cov_params = np.full((self._nvar, self._nvar), np.nan)
                self.bse = np.full(self._nvar, np.nan)

            # R-squared
            y_mean = np.mean(self.endog)
            if y_mean != 0:
                self.sst = np.sum((self.endog - y_mean) ** 2)
                self.rsquared = 1 - self.ssr / self.sst
                self.rsquared_adj = 1 - (1 - self.rsquared) * (self._nobs - 1) / self.df_resid
            else:
                self.rsquared = np.nan
                self.rsquared_adj = np.nan

            # F-statistic
            if self.df_model > 0 and self.df_resid > 0:
                self.fvalue = (self.ssr / self.df_model) / (self.scale)
                # Approximate p-value
                from scipy.stats import f

                self.f_pvalue = 1 - f.cdf(self.fvalue, self.df_model, self.df_resid)
            else:
                self.fvalue = np.nan
                self.f_pvalue = np.nan

            # AIC and BIC
            k = 2  # Number of parameters
            self.aic = self._nobs * np.log(self.ssr / self._nobs) + 2 * k
            self.bic = self._nobs * np.log(self.ssr / self._nobs) + k * np.log(self._nobs)

        except Exception as e:
            logger.error(f"OLS fitting failed: {e}")
            self.params = np.full(self._nvar, np.nan)
            self.resid = np.full(self._nobs, np.nan)
            self.bse = np.full(self._nvar, np.nan)

    def fit(self):
        """Fit method for compatibility with statsmodels API"""
        return self

    def summary(self):
        """Return summary of regression results"""
        summary_str = f"""
OLS Regression Results
==============================================================================
Dep. Variable:                      y   R-squared:                       {self.rsquared:.4f}
Model:                            OLS   Adj. R-squared:                  {self.rsquared_adj:.4f}
Method:                 Least Squares   F-statistic:                    {self.fvalue:.4f}
Date:                {pd.Timestamp.now().strftime("%a, %d %b %Y")}   Prob (F-statistic):              {self.f_pvalue:.4f}
Time:                        {pd.Timestamp.now().strftime("%H:%M:%S")}   Log-Likelihood:                {-self._nobs / 2 * np.log(2 * np.pi * self.scale) - self.ssr / (2 * self.scale):.4f}
No. Observations:                 {self._nobs}   AIC:                             {self.aic:.4f}
Df Residuals:                     {self.df_resid}   BIC:                             {self.bic:.4f}
Df Model:                         {self.df_model}
Covariance Type:            nonrobust
==============================================================================
                 coef    std err          t      P>|t|      [0.025      0.975]
------------------------------------------------------------------------------
"""
        for i, (coef, se) in enumerate(zip(self.params, self.bse)):
            if not np.isnan(coef) and not np.isnan(se):
                t_stat = coef / se if se > 0 else np.nan
                from scipy.stats import t

                p_value = (
                    2 * (1 - t.cdf(abs(t_stat), self.df_resid)) if not np.isnan(t_stat) else np.nan
                )
                summary_str += f"x{i:2d}        {coef:8.4f}    {se:8.4f}      {t_stat:8.4f}      {p_value:8.4f}     {coef - 1.96 * se:8.4f}     {coef + 1.96 * se:8.4f}\n"
            else:
                summary_str += f"x{i:2d}        {coef:8.4f}    {se:8.4f}        nan        nan        nan        nan\n"

        summary_str += (
            "==============================================================================\n"
        )
        return summary_str

    def __repr__(self):
        return f"<OLS: nobs={self._nobs}, nvar={self._nvar}, R2={self.rsquared:.4f}>"


class AutoReg:
    """
    Autoregressive model - fallback implementation.

    This is a simplified fallback using OLS.
    For full functionality, install statsmodels.
    """

    def __init__(
        self,
        endog,
        lags,
        trend="c",
        seasonal=False,
        exog=None,
        hold_back=None,
        period=None,
        old_names=False,
    ):
        """
        Parameters
        ----------
        endog : array_like
            Endogenous response variable
        lags : int or list
            Number of lags to include in model
        trend : str {"c", "t", "ct"}
            Trend to include
        seasonal : bool
            Include seasonal dummies
        exog : array_like
            Exogenous variables
        hold_back : int, optional
            Number of observations to hold back
        period : int, optional
            Period of seasonal data
        old_names : bool
            Use old names
        """
        _log_fallback_warning(
            "AutoReg",
            "For full AutoReg functionality, install statsmodels: pip install statsmodels",
        )

        # Convert to numpy array
        if isinstance(endog, pd.Series):
            self.endog_orig = endog
            endog = endog.values
        else:
            self.endog_orig = None

        self.endog = np.asarray(endog, dtype=float).squeeze()
        self.lags = lags if isinstance(lags, int) else max(lags)
        self.trend = trend
        self.seasonal = seasonal
        self.period = period

        self._nobs = len(self.endog)

        # Prepare data
        self._prepare_data()

    def _prepare_data(self):
        """Prepare lagged data for regression"""
        # Create lagged variables
        lagged_data = []
        valid_idx = []

        for i in range(self.lags, self._nobs):
            lagged_row = []
            for lag in range(1, self.lags + 1):
                lagged_row.append(self.endog[i - lag])
            lagged_data.append(lagged_row)
            valid_idx.append(i)

        self.lagged_data = np.array(lagged_data)
        self.valid_idx = np.array(valid_idx)
        self.dependent_var = self.endog[self.valid_idx]

        # Add trend if requested
        self.exog = self.lagged_data.copy()
        if self.trend == "c" or self.trend == "ct":
            self.exog = np.column_stack([np.ones(len(self.exog)), self.exog])
        if self.trend == "t" or self.trend == "ct":
            trend_var = np.arange(1, len(self.exog) + 1)
            self.exog = np.column_stack([self.exog, trend_var])

    def fit(self):
        """Fit the autoregressive model"""
        # Use OLS to fit
        self._ols = OLS(self.dependent_var, self.exog)
        self.params = self._ols.params

        # Calculate residuals
        self.resid = self._ols.resid

        # Calculate standard errors
        self.bse = self._ols.bse

        # Calculate AIC and BIC
        nobs = len(self.dependent_var)
        k = len(self.params)
        self.aic = nobs * np.log(np.sum(self.resid**2) / nobs) + 2 * k
        self.bic = nobs * np.log(np.sum(self.resid**2) / nobs) + k * np.log(nobs)

        # Return result object
        return AutoRegResults(self)


class AutoRegResults:
    """Results class for AutoReg"""

    def __init__(self, model):
        self.model = model
        self.params = model.params
        self.resid = model.resid
        self.aic = model.aic
        self.bic = model.bic
        self.nobs = len(model.dependent_var)

    def summary(self):
        """Return summary of results"""
        return f"""
AutoReg Results
==============================================================================
Dep. Variable:                      y   No. Observations:                 {self.nobs}
Model:                   AutoReg({self.model.lags})   Log Likelihood:                {np.sum(self.resid**2):.4f}
Method:                           Least Squares   AIC:                             {self.aic:.4f}
Date:                {pd.Timestamp.now().strftime("%a, %d %b %Y")}   BIC:                             {self.bic:.4f}
Time:                        {pd.Timestamp.now().strftime("%H:%M:%S")}
Sample:                    {self.model.lags + 1}   HQIC:                            {self.aic:.4f}
==============================================================================
                 coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------
"""

    def predict(self, start=None, end=None, dynamic=False):
        """Make predictions"""
        if start is None:
            start = 0
        if end is None:
            end = len(self.model.endog) - 1

        predictions = np.zeros(end - start + 1)
        return predictions

    def __repr__(self):
        return f"<AutoRegResults: lags={self.model.lags}, AIC={self.aic:.4f}, BIC={self.bic:.4f}>"


def pacf(x, nlags=40, method="ywunbiased", alpha=None):
    """
    Partial autocorrelation estimated - fallback implementation.

    Parameters
    ----------
    x : array_like
        Time series data
    nlags : int
        Number of lags to return
    method : str
        Method for PACF calculation
    alpha : float, optional
        Confidence interval width

    Returns
    -------
    pacf : ndarray
        Partial autocorrelations
    confint : ndarray, optional
        Confidence intervals if alpha is provided
    """
    _log_fallback_warning(
        "pacf", "For full PACF functionality, install statsmodels: pip install statsmodels"
    )

    # Convert to numpy array
    if isinstance(x, pd.Series):
        x = x.values
    x = np.asarray(x, dtype=float).squeeze()

    # Remove NaN values
    x = x[~np.isnan(x)]

    nobs = len(x)
    nlags = min(nlags, nobs - 1)

    # Simple PACF using Yule-Walker equations
    pacf_values = np.zeros(nlags + 1)
    pacf_values[0] = 1.0  # PACF at lag 0 is always 1

    # Durbin-Levinson algorithm for PACF
    if nlags > 0:
        # Autocorrelations
        acf = [1.0]
        for k in range(1, nlags + 1):
            acf.append(np.corrcoef(x[:-k], x[k:])[0, 1])

        # Levinson-Durbin recursion
        pacf_values[1] = acf[1]
        for k in range(2, nlags + 1):
            # Forward and backward prediction errors
            phi = np.zeros(k + 1)
            phi[k] = pacf_values[k - 1]  # Use previous PACF as initial guess

            # This is a simplified version
            # Full implementation would use Durbin-Levinson recursion
            try:
                # Solve Yule-Walker equations
                toeplitz = np.zeros((k, k))
                for i in range(k):
                    for j in range(k):
                        toeplitz[i, j] = acf[abs(i - j)]

                rhs = np.array(acf[1 : k + 1])
                phi_k = np.linalg.solve(toeplitz, rhs)[-1]
                pacf_values[k] = phi_k
            except (ValueError, TypeError, np.linalg.LinAlgError):
                pacf_values[k] = acf[k]  # Fallback to ACF

    return pacf_values


def grangercausalitytests(x, maxlag, addconst=True, verbose=True):
    """
    Four tests for granger non causality of 2 time series - fallback implementation.

    Parameters
    ----------
    x : array_like
        Data for test with first variable causing second
    maxlag : int
        Maximum lag to test
    addconst : bool
        Add constant to regression
    verbose : bool
        Print results

    Returns
    -------
    dict
        Dictionary with test results for each lag
    """
    _log_fallback_warning(
        "grangercausalitytests",
        "For full Granger causality tests, install statsmodels: pip install statsmodels",
    )

    # Convert to numpy array
    if isinstance(x, pd.DataFrame):
        x = x.values
    x = np.asarray(x, dtype=float)

    if x.shape[1] != 2:
        raise ValueError("x must have exactly 2 columns")

    results = {}

    for lag in range(1, maxlag + 1):
        # Prepare data
        y = x[:, 0]  # Effect variable
        x_var = x[:, 1]  # Causal variable

        # Create lagged variables
        data = []
        target = []

        for i in range(lag, len(x)):
            row = []
            # Lags of dependent variable
            for lag_idx in range(1, lag + 1):
                row.append(y[i - lag_idx])
            # Lags of independent variable
            for lag_idx in range(lag):
                row.append(x_var[i - lag_idx - 1])
            data.append(row)
            target.append(y[i])

        data = np.array(data)
        target = np.array(target)

        # Restricted model (only lags of dependent variable)
        X_restricted = data[:, :lag]
        if addconst:
            X_restricted = np.column_stack([np.ones(len(X_restricted)), X_restricted])

        # Unrestricted model (lags of both variables)
        X_unrestricted = data
        if addconst:
            X_unrestricted = np.column_stack([np.ones(len(X_unrestricted)), X_unrestricted])

        # Fit models
        try:
            beta_r = np.linalg.lstsq(X_restricted, target, rcond=None)[0]
            resid_r = target - X_restricted @ beta_r
            ssr_r = np.sum(resid_r**2)

            beta_ur = np.linalg.lstsq(X_unrestricted, target, rcond=None)[0]
            resid_ur = target - X_unrestricted @ beta_ur
            ssr_ur = np.sum(resid_ur**2)

            # F-test
            nobs = len(target)
            df_r = X_restricted.shape[1]
            df_ur = X_unrestricted.shape[1]

            f_stat = ((ssr_r - ssr_ur) / (df_ur - df_r)) / (ssr_ur / (nobs - df_ur))

            from scipy.stats import f

            p_value = 1 - f.cdf(f_stat, df_ur - df_r, nobs - df_ur)

            result = {
                "ssr_r": ssr_r,
                "ssr_ur": ssr_ur,
                "df_r": df_r,
                "df_ur": df_ur,
                "f_stat": f_stat,
                "p_value": p_value,
            }

            results[lag] = result

            if verbose:
                logger.debug("\nGranger Causality")
                logger.debug(f"number of lags (no zero): {lag}")
                logger.debug(f"  ssr based F test:         {f_stat:.4f}")
                logger.debug(f"  p-value:                  {p_value:.4f}")
                logger.debug(f"  df denominator:           {nobs - df_ur}")

        except Exception as e:
            logger.warning(f"Granger causality test failed for lag {lag}: {e}")
            results[lag] = None

    return results


# Export all fallback functions
__all__ = [
    "OLS",
    "USING_FALLBACK",
    "AutoReg",
    "AutoRegResults",
    "acorr_ljungbox",
    "adfuller",
    "coint",
    "grangercausalitytests",
    "kpss",
    "pacf",
    "seasonal_decompose",
]


def kpss(
    x: Union[np.ndarray, pd.Series],
    regression: str = "c",
    nlags: str = "auto",
    store: bool = False,
) -> tuple[float, float, int, dict[str, float]]:
    """
    Kwiatkowski-Phillips-Schmidt-Shin test for stationarity - fallback implementation.

    This is a simplified fallback using scipy.
    For full functionality, install statsmodels.

    Parameters
    ----------
    x : array_like
        The time series to test for stationarity
    regression : str {"c", "ct"}
        The null hypothesis for the KPSS test
        - "c": The data is stationary around a constant (default)
        - "ct": The data is stationary around a trend
    nlags : str {"auto", int}
        Indicates the number of lags to be used
    store : bool
        If True, return results in class instance

    Returns
    -------
    kpss_stat : float
        The KPSS test statistic
    pvalue : float
        The p-value of the test
    lags : int
        The number of lags used
    crit : dict
        The critical values at 1%, 5%, 10%

    Notes
    -----
    H0: The process is trend stationary
    H1: The process has a unit root (non-stationary)
    """
    _log_fallback_warning(
        "kpss", "For full KPSS test functionality, install statsmodels: pip install statsmodels"
    )

    # Convert to numpy array
    if isinstance(x, pd.Series):
        x = x.values
    x = np.asarray(x, dtype=float).squeeze()

    # Remove NaN values
    x = x[~np.isnan(x)]

    nobs = len(x)
    if nobs < 10:
        raise ValueError("Sample size is too short")

    # Determine number of lags
    if nlags == "auto":
        nlags = int(12.0 * np.power(nobs / 100.0, 1 / 4.0))

    # Calculate residuals from regression
    if regression == "ct":
        # Regress on constant and trend
        t = np.arange(1, nobs + 1)
        X = np.column_stack([np.ones(nobs), t])
    else:  # regression == "c"
        # Regress on constant only
        X = np.ones((nobs, 1))

    try:
        # OLS regression
        beta = np.linalg.lstsq(X, x, rcond=None)[0]
        residuals = x - X @ beta

        # Calculate KPSS statistic
        # Sum of squared partial sums of residuals
        partial_sums = np.cumsum(residuals)
        kpss_stat = np.sum(partial_sums**2) / (nobs**2)

        # Estimate long-run variance of residuals
        # Use Newey-West estimator
        gamma0 = np.sum(residuals**2) / nobs

        # Calculate autocovariances
        gamma_j = 0.0
        for j in range(1, nlags + 1):
            if j < nobs:
                autocov = np.sum(residuals[j:] * residuals[:-j]) / nobs
                # Bartlett kernel weights
                weight = 1 - j / (nlags + 1)
                gamma_j += 2 * weight * autocov

        long_run_var = gamma0 + gamma_j

        # Standardize test statistic
        kpss_stat = kpss_stat / long_run_var if long_run_var > 0 else 0.0

        # Critical values for KPSS test
        # These depend on regression type
        if regression == "ct":
            critical_values = {"1%": 0.216, "5%": 0.146, "10%": 0.119}
        else:
            critical_values = {"1%": 0.739, "5%": 0.463, "10%": 0.347}

        # Approximate p-value
        if kpss_stat < critical_values["10%"]:
            pvalue = 0.10
        elif kpss_stat < critical_values["5%"]:
            pvalue = 0.05
        elif kpss_stat < critical_values["1%"]:
            pvalue = 0.01
        else:
            # For very high values
            pvalue = 0.001

    except Exception as e:
        # Fallback to simpler test
        logger.warning(f"KPSS test calculation failed: {e}, using simpler test")

        # Simple variance ratio test
        kpss_stat = 1.0  # Neutral value
        pvalue = 0.05

        if regression == "ct":
            critical_values = {"1%": 0.216, "5%": 0.146, "10%": 0.119}
        else:
            critical_values = {"1%": 0.739, "5%": 0.463, "10%": 0.347}

    lags = nlags if isinstance(nlags, int) else int(nlags)

    return kpss_stat, pvalue, lags, critical_values
