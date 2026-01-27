
    def _validate_configurations(self) -> None:
        """
        Validate all configurations on startup.

        This method performs comprehensive validation of:
        - Config file existence
        - ProfileConfigLoader functionality
        - ProfileStrategyMapper functionality
        - Config key consistency
        - Tier mapping consistency

        All issues are logged as warnings, not errors, to avoid breaking startup.
        """
        logger.info("=" * 80)
        logger.info("Starting Configuration Validation")
        logger.info("=" * 80)

        validation_results = {
            "config_files": self._validate_config_file_exists(),
            "profile_config_loader": self._validate_profile_config_loader(),
            "profile_strategy_mapper": self._validate_profile_strategy_mapper(),
            "config_keys": self._validate_config_keys_match(),
            "tier_mappings": self._validate_tier_mappings(),
        }

        # Summary
        total_checks = sum(len(v) if isinstance(v, dict) else 1 for v in validation_results.values())
        passed_checks = sum(
            1 for v in validation_results.values()
            if isinstance(v, dict) and all(p is None for p in v.values())
        )

        logger.info("=" * 80)
        logger.info(f"Configuration Validation Complete: {passed_checks}/{total_checks} checks passed")
        logger.info("=" * 80)

        # Log detailed results
        for category, result in validation_results.items():
            if isinstance(result, dict):
                issues = [k for k, v in result.items() if v is not None]
                if issues:
                    logger.warning(f"  {category}: {len(issues)} issue(s) - {', '.join(issues)}")
                else:
                    logger.info(f"  {category}: OK")
            else:
                if result is not None:
                    logger.warning(f"  {category}: {result}")
                else:
                    logger.info(f"  {category}: OK")

    def _validate_config_file_exists(self) -> Dict[str, Optional[str]]:
        """
        Validate that all referenced config files exist.

        Returns:
            Dictionary with file paths as keys and error messages as values (None if OK)
        """
        issues = {}

        # Check main config file
        if not self.config_path.exists():
            issues[str(self.config_path)] = f"Main config file not found: {self.config_path}"

        # Check ProfileConfigLoader config file
        try:
            from app.core.config.profile_config_loader import ProfileConfigLoader
            profile_optimization_path = Path("config/backtesting/profile_optimization.yaml")
            if not profile_optimization_path.exists():
                issues[str(profile_optimization_path)] = f"Profile optimization config not found: {profile_optimization_path}"
        except Exception as e:
            issues["ProfileConfigLoader.config"] = f"Cannot verify ProfileConfigLoader config: {e}"

        # Check database parent directory
        db_url = self.config.get("database", {}).get("url", "sqlite:///profile_backtest_results.db")
        if db_url.startswith("sqlite:///"):
            db_path = Path(db_url.replace("sqlite:///", ""))
            if db_path.parent != Path(".") and not db_path.parent.exists():
                issues[db_path] = f"Database parent directory does not exist: {db_path.parent}"

        # Check output directory
        output_dir = Path(self.config.get("output_dir", "results/profile_batch_backtesting"))
        # Note: output_dir is created later, so we just warn if parent doesn't exist
        if output_dir.parent != Path(".") and not output_dir.parent.exists():
            issues[str(output_dir)] = f"Output directory parent does not exist: {output_dir.parent}"

        if issues:
            for path, error in issues.items():
                logger.warning(f"[CONFIG FILE] {error}")
        else:
            logger.info("[CONFIG FILE] All referenced config files exist")

        return issues

    def _validate_profile_config_loader(self) -> Dict[str, Optional[str]]:
        """
        Validate ProfileConfigLoader can load configurations.

        Returns:
            Dictionary with config keys as keys and error messages as values (None if OK)
        """
        issues = {}

        if self.profile_config_loader is None:
            issues["ProfileConfigLoader"] = "ProfileConfigLoader not initialized"
            logger.warning("[PROFILE CONFIG LOADER] Loader not initialized, using fallback defaults")
            return issues

        # Test loading various configs
        test_configs = [
            ("threshold_config", "rsi"),
            ("walk_forward_config", None),
            ("monte_carlo_config", None),
            ("validation_thresholds", None),
        ]

        for method_name, param in test_configs:
            try:
                if method_name == "threshold_config":
                    config = self.profile_config_loader.get_threshold_config(param)
                elif method_name == "walk_forward_config":
                    config = self.profile_config_loader.get_walk_forward_config()
                elif method_name == "monte_carlo_config":
                    config = self.profile_config_loader.get_monte_carlo_config()
                elif method_name == "validation_thresholds":
                    config = self.profile_config_loader.get_validation_thresholds()

                if not isinstance(config, dict):
                    issues[f"{method_name}({param})"] = f"Expected dict, got {type(config)}"
                else:
                    logger.debug(f"[PROFILE CONFIG LOADER] {method_name}({param}): OK")
            except Exception as e:
                issues[f"{method_name}({param})"] = str(e)

        if issues:
            for key, error in issues.items():
                logger.warning(f"[PROFILE CONFIG LOADER] {key}: {error}")
        else:
            logger.info("[PROFILE CONFIG LOADER] All config types loadable")

        return issues

    def _validate_profile_strategy_mapper(self) -> Dict[str, Optional[str]]:
        """
        Validate ProfileStrategyMapper can create strategy mappings.

        Returns:
            Dictionary with test cases as keys and error messages as values (None if OK)
        """
        issues = {}

        if self.profile_mapper is None:
            issues["ProfileStrategyMapper"] = "ProfileStrategyMapper not initialized"
            logger.warning("[PROFILE STRATEGY MAPPER] Mapper not initialized, multi-strategy disabled")
            return issues

        # Test with a sample profile
        try:
            from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
            from decimal import Decimal

            test_profile = InputProfile(
                capital_initial=Decimal("100000"),
                objetivo_inversion=ObjectivoInversion.CRECIMIENTO,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=24,
            )

            # Test map_profile_to_strategies
            try:
                strategy_config = self.profile_mapper.map_profile_to_strategies(test_profile)

                # Check expected keys
                expected_keys = ["enabled_strategies", "risk_params", "trading_params",
                               "learning_engines", "ensemble_config"]
                missing_keys = [k for k in expected_keys if k not in strategy_config]
                if missing_keys:
                    issues["map_profile_to_strategies"] = f"Missing keys: {missing_keys}"
                else:
                    logger.debug("[PROFILE STRATEGY MAPPER] map_profile_to_strategies: OK")
            except Exception as e:
                issues["map_profile_to_strategies"] = str(e)

            # Test create_strategy_mapping
            try:
                strategy_mapping = self.profile_mapper.create_strategy_mapping(test_profile)

                # Check StrategyMapping attributes
                required_attrs = ["enabled_strategies", "ensemble_mode", "strategy_weights"]
                missing_attrs = [a for a in required_attrs if not hasattr(strategy_mapping, a)]
                if missing_attrs:
                    issues["create_strategy_mapping"] = f"Missing attributes: {missing_attrs}"
                else:
                    logger.debug("[PROFILE STRATEGY MAPPER] create_strategy_mapping: OK")
            except Exception as e:
                issues["create_strategy_mapping"] = str(e)

        except Exception as e:
            issues["test_profile"] = f"Cannot create test profile: {e}"

        if issues:
            for key, error in issues.items():
                logger.warning(f"[PROFILE STRATEGY MAPPER] {key}: {error}")
        else:
            logger.info("[PROFILE STRATEGY MAPPER] All mapper functions operational")

        return issues

    def _validate_config_keys_match(self) -> Dict[str, Optional[str]]:
        """
        Validate that config keys match what loaders expect.

        This checks consistency between:
        - profile_batch_backtest.yaml (workflow config)
        - profile_optimization.yaml (parameter config, loaded via ProfileConfigLoader)

        Returns:
            Dictionary with mismatch descriptions as keys and error messages as values (None if OK)
        """
        issues = {}

        # Check workflow config has expected top-level keys
        expected_top_level_keys = [
            "capital_tiers",
            "investment_horizons",
            "optimization",
            "validation",
            "database",
            "output_dir",
        ]

        missing_keys = [k for k in expected_top_level_keys if k not in self.config]
        if missing_keys:
            issues[f"workflow_config.top_level"] = f"Missing keys: {missing_keys}"

        # Check optimization config has expected structure
        optimization_config = self.config.get("optimization", {})
        expected_optimization_keys = ["n_trials", "timeout"]
        missing_opt_keys = [k for k in expected_optimization_keys if k not in optimization_config]
        if missing_opt_keys:
            issues[f"workflow_config.optimization"] = f"Missing keys: {missing_opt_keys}"

        # Check validation config has expected structure
        validation_config = self.config.get("validation", {})
        expected_validation_sections = ["walk_forward", "monte_carlo", "out_of_sample"]
        missing_val_sections = [s for s in expected_validation_sections if s not in validation_config]
        if missing_val_sections:
            issues[f"workflow_config.validation"] = f"Missing sections: {missing_val_sections}"

        # Check ProfileConfigLoader keys if available
        if self.profile_config_loader is not None:
            try:
                # Test that we can access expected nested keys
                wf_config = self.profile_config_loader.get_walk_forward_config()
                if not isinstance(wf_config, dict):
                    issues["profile_config_loader.walk_forward"] = f"Expected dict, got {type(wf_config)}"

                mc_config = self.profile_config_loader.get_monte_carlo_config()
                if not isinstance(mc_config, dict):
                    issues["profile_config_loader.monte_carlo"] = f"Expected dict, got {type(mc_config)}"
            except Exception as e:
                issues["profile_config_loader.access"] = str(e)

        if issues:
            for key, error in issues.items():
                logger.warning(f"[CONFIG KEYS] {key}: {error}")
        else:
            logger.info("[CONFIG KEYS] All config structures match expected format")

        return issues

    def _validate_tier_mappings(self) -> Dict[str, Optional[str]]:
        """
        Validate that tier mappings are consistent across the system.

        This checks consistency between:
        - InputProfile.capital_flag (small, medium, large)
        - Config tiers (bajo, medio, alto)
        - TierMapper mappings

        Returns:
            Dictionary with tier checks as keys and error messages as values (None if OK)
        """
        issues = {}

        # Check capital_tiers in config
        capital_tiers = self.config.get("capital_tiers", {})
        expected_tier_keys = ["bajo", "medio", "alto"]
        missing_tier_keys = [k for k in expected_tier_keys if k not in capital_tiers]
        if missing_tier_keys:
            issues["config.capital_tiers"] = f"Missing tier keys: {missing_tier_keys}"

        # Validate tier values are positive numbers
        for tier_key, tier_value in capital_tiers.items():
            try:
                value = float(tier_value)
                if value <= 0:
                    issues[f"config.capital_tiers.{tier_key}"] = f"Invalid value: {tier_value} (must be positive)"
            except (ValueError, TypeError):
                issues[f"config.capital_tiers.{tier_key}"] = f"Invalid value: {tier_value} (not a number)"

        # Test tier mapper
        try:
            from app.core.tier_mapper import map_profile_tier_to_config

            test_mappings = [
                ("small", "spanish", "bajo"),
                ("medium", "spanish", "medio"),
                ("large", "spanish", "alto"),
            ]

            for from_tier, target_format, expected in test_mappings:
                try:
                    result = map_profile_tier_to_config(from_tier, target_format)
                    if result != expected:
                        issues[f"tier_mapper.{from_tier}_to_{target_format}"] = (
                            f"Expected '{expected}', got '{result}'"
                        )
                except Exception as e:
                    issues[f"tier_mapper.{from_tier}_to_{target_format}"] = str(e)

        except ImportError:
            issues["tier_mapper.import"] = "Cannot import tier_mapper"
        except Exception as e:
            issues["tier_mapper.test"] = str(e)

        # Test _get_capital_tier_key method
        try:
            from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
            from decimal import Decimal

            test_cases = [
                (Decimal("30000"), "bajo"),
                (Decimal("100000"), "medio"),
                (Decimal("500000"), "alto"),
            ]

            for capital, expected_tier in test_cases:
                test_profile = InputProfile(
                    capital_initial=capital,
                    objetivo_inversion=ObjectivoInversion.CRECIMIENTO,
                    risk_tolerance=RiskTolerance.MEDIO,
                    investment_horizon=24,
                )
                try:
                    result = self._get_capital_tier_key(test_profile)
                    if result != expected_tier:
                        issues[f"_get_capital_tier_key.{capital}"] = (
                            f"Expected '{expected_tier}', got '{result}'"
                        )
                except Exception as e:
                    issues[f"_get_capital_tier_key.{capital}"] = str(e)

        except Exception as e:
            issues["_get_capital_tier_key.test"] = str(e)

        if issues:
            for key, error in issues.items():
                logger.warning(f"[TIER MAPPINGS] {key}: {error}")
        else:
            logger.info("[TIER MAPPINGS] All tier mappings consistent")

        return issues
