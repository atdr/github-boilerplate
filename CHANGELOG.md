# Changelog

## [1.3.1](https://github.com/atdr/github-boilerplate/compare/v1.3.0...v1.3.1) (2026-11-28)


### Bug Fixes

* **configure:** check and enforce the publishing environments' branch policy ([#81](https://github.com/atdr/github-boilerplate/issues/81)) ([80df2ea](https://github.com/atdr/github-boilerplate/commit/80df2ea8b68191ff6ced2195b2397be1d4d57ea7))
* **deps:** Bump astral-sh/setup-uv in / ([#83](https://github.com/atdr/github-boilerplate/issues/83)) ([9fe6785](https://github.com/atdr/github-boilerplate/commit/9fe678522a830ccf2b4fdb06a882c8b47759b53e))

## [1.3.0](https://github.com/atdr/github-boilerplate/compare/v1.2.0...v1.3.0) (2026-11-17)


### Features

* **auto-merge:** pilot auto-merge for owner PRs that Copilot approved ([#79](https://github.com/atdr/github-boilerplate/issues/79)) ([ea2f711](https://github.com/atdr/github-boilerplate/commit/ea2f711aaa2c89ba4ebbb877f7eebb76a0473748))
* **python-ci:** audit runtime dependencies with pip-audit ([#74](https://github.com/atdr/github-boilerplate/issues/74)) ([eb14453](https://github.com/atdr/github-boilerplate/commit/eb14453197334509766424f71ec1ea5f0bbb5578))
* **template:** run the release workflows on a daily schedule ([#72](https://github.com/atdr/github-boilerplate/issues/72)) ([6c3bac4](https://github.com/atdr/github-boilerplate/commit/6c3bac4039e51158ca6cb79d85c29c9b95e2e776))


### Bug Fixes

* **configure:** require a gate only where its job exists ([#73](https://github.com/atdr/github-boilerplate/issues/73)) ([070d8e6](https://github.com/atdr/github-boilerplate/commit/070d8e6065579afed09b0c3106d1a7d3ae27dd1f))

## [1.2.0](https://github.com/atdr/github-boilerplate/compare/v1.1.0...v1.2.0) (2026-11-16)


### Features

* **template:** link each publish deployment to its registry page ([#48](https://github.com/atdr/github-boilerplate/issues/48)) ([1736a5f](https://github.com/atdr/github-boilerplate/commit/1736a5ff9687d9d22c655115ca23fe2b37281228))


### Bug Fixes

* **apply:** guard the empty copied array under bash 3.2 ([#70](https://github.com/atdr/github-boilerplate/issues/70)) ([7f77f25](https://github.com/atdr/github-boilerplate/commit/7f77f25da90a0a9527181b3819010170bb1a0a13))
* **auto-merge:** switch auto-merge off when a bump stops qualifying ([#69](https://github.com/atdr/github-boilerplate/issues/69)) ([8f84107](https://github.com/atdr/github-boilerplate/commit/8f841077334d4ac3a2c64105b19826cc82744cb5))
* **configure:** reject arguments after the mode ([#66](https://github.com/atdr/github-boilerplate/issues/66)) ([7308b6d](https://github.com/atdr/github-boilerplate/commit/7308b6d92844afec375a7afcf033c2ff9228475f))
* **template:** keep .env.example trackable outside Node ([#68](https://github.com/atdr/github-boilerplate/issues/68)) ([b026b9c](https://github.com/atdr/github-boilerplate/commit/b026b9cdd2e47219b85aa63a622ccb8bc6c4f335))
* **template:** match pre-commit mdformat pins to the CI pins ([#67](https://github.com/atdr/github-boilerplate/issues/67)) ([41b226e](https://github.com/atdr/github-boilerplate/commit/41b226e2e5206eba8398636d551e947ec070e8e3))

## [1.1.0](https://github.com/atdr/github-boilerplate/compare/v1.0.0...v1.1.0) (2026-11-15)


### Features

* auto-merge Dependabot's patch and minor bumps ([#44](https://github.com/atdr/github-boilerplate/issues/44)) ([875b55f](https://github.com/atdr/github-boilerplate/commit/875b55f625b91e8fa79e95dfc21f1d56c45d4c71))

## [1.0.0](https://github.com/atdr/github-boilerplate/compare/v0.4.0...v1.0.0) (2026-11-15)


### Features

* **configure:** let a repo opt its admin out of the ruleset ([#40](https://github.com/atdr/github-boilerplate/issues/40)) ([e5bcc32](https://github.com/atdr/github-boilerplate/commit/e5bcc32e79a791daac1021682b2062723598ae21))


### Miscellaneous Chores

* release 1.0.0 ([#43](https://github.com/atdr/github-boilerplate/issues/43)) ([5951b2e](https://github.com/atdr/github-boilerplate/commit/5951b2e7d2a817213939275adf286d5e2351f3e7))

## [0.4.0](https://github.com/atdr/github-boilerplate/compare/v0.3.2...v0.4.0) (2026-11-08)


### ⚠ BREAKING CHANGES

* **conventions:** the conventions check fails on a codecov.yml that sets `informational: true` on either status or has no `threshold` on `project`. Update codecov.yml to match template/python/codecov.yml when taking this release.

### Features

* **conventions:** require Codecov statuses that can fail ([#38](https://github.com/atdr/github-boilerplate/issues/38)) ([868f834](https://github.com/atdr/github-boilerplate/commit/868f834b09a9e40c3e8d8ad2767d59e83db84f58))


### Bug Fixes

* **configure:** report classic branch protection the ruleset leaves ([#37](https://github.com/atdr/github-boilerplate/issues/37)) ([c9e4119](https://github.com/atdr/github-boilerplate/commit/c9e41198a244bcf6560cb88d7ad7207cd4eb090d))
* **tex:** note the package list fallback branch in compile.yml ([#33](https://github.com/atdr/github-boilerplate/issues/33)) ([18d5878](https://github.com/atdr/github-boilerplate/commit/18d587825df7572ded5bac891a4c279e35ec5497))

## [0.3.2](https://github.com/atdr/github-boilerplate/compare/v0.3.1...v0.3.2) (2026-11-07)


### Bug Fixes

* **deps:** Bump astral-sh/setup-uv in / ([#31](https://github.com/atdr/github-boilerplate/issues/31)) ([395d25d](https://github.com/atdr/github-boilerplate/commit/395d25d034910b686de796d33ac59d8b42a47b41))
* **deps:** Bump mdformat-frontmatter from 2.1.2 to 2.2.0 in /scripts ([#28](https://github.com/atdr/github-boilerplate/issues/28)) ([571b38a](https://github.com/atdr/github-boilerplate/commit/571b38abfdee6d529dfd14e157f7e78c542624b6))
* **template:** state a security policy that holds without release-please ([#27](https://github.com/atdr/github-boilerplate/issues/27)) ([189ad4a](https://github.com/atdr/github-boilerplate/commit/189ad4ac695bf792656daf07baf52eafe713759f))

## [0.3.1](https://github.com/atdr/github-boilerplate/compare/v0.3.0...v0.3.1) (2026-10-31)


### Bug Fixes

* **template:** leave .bib files to the reference manager, as CI does ([#24](https://github.com/atdr/github-boilerplate/issues/24)) ([67cf2f0](https://github.com/atdr/github-boilerplate/commit/67cf2f0c0a46de161fdba10afd50fccca8fd2f11))
* **template:** ship codecov.yml only with the Node and Python overlays ([#25](https://github.com/atdr/github-boilerplate/issues/25)) ([8cbce9b](https://github.com/atdr/github-boilerplate/commit/8cbce9b4e77a561de5585ed5e83ab0668a77e791))

## [0.3.0](https://github.com/atdr/github-boilerplate/compare/v0.2.3...v0.3.0) (2026-10-31)


### Features

* **scripts:** require only the gates a repo's workflows report ([#20](https://github.com/atdr/github-boilerplate/issues/20)) ([656799e](https://github.com/atdr/github-boilerplate/commit/656799eb9d6bb9b38f5131f988f1c700694b610f))
* **scripts:** show how a repo's copies differ from the template ([#22](https://github.com/atdr/github-boilerplate/issues/22)) ([cef2ab2](https://github.com/atdr/github-boilerplate/commit/cef2ab2a30cf4157a9baf3c81155dee29ddfdef5))


### Bug Fixes

* **deps:** Bump DavidAnson/markdownlint-cli2-action in / ([#19](https://github.com/atdr/github-boilerplate/issues/19)) ([3254a4b](https://github.com/atdr/github-boilerplate/commit/3254a4b79f1abc1849a8286d33e9416c8c1038ff))
* **template:** keep manual TeX runs, and run mdformat's hook on Python 3.13 ([#23](https://github.com/atdr/github-boilerplate/issues/23)) ([15ce352](https://github.com/atdr/github-boilerplate/commit/15ce35278bf0b47dd9a8bc4ecd74cfa1a63828c2))

## [0.2.3](https://github.com/atdr/github-boilerplate/compare/v0.2.2...v0.2.3) (2026-10-29)


### Bug Fixes

* **template:** give CI runs on main a concurrency group each ([#16](https://github.com/atdr/github-boilerplate/issues/16)) ([92f73f9](https://github.com/atdr/github-boilerplate/commit/92f73f9abc8c32047177467f24add4a1aab8953b))
* **template:** let atdr's own actions skip Dependabot's cooldown ([#18](https://github.com/atdr/github-boilerplate/issues/18)) ([62abab6](https://github.com/atdr/github-boilerplate/commit/62abab6355daf2394a86face921a04df6c00fa89))

## [0.2.2](https://github.com/atdr/github-boilerplate/compare/v0.2.1...v0.2.2) (2026-10-29)


### Bug Fixes

* **workflows:** keep GitHub alert markers on their own line under mdformat ([#15](https://github.com/atdr/github-boilerplate/issues/15)) ([85a9fbe](https://github.com/atdr/github-boilerplate/commit/85a9fbe8484eb95a2d1fc1da512f00c450554f34))
* **workflows:** keep Markdown footnotes intact under mdformat ([#13](https://github.com/atdr/github-boilerplate/issues/13)) ([0cbbe49](https://github.com/atdr/github-boilerplate/commit/0cbbe4910c1b1d52a6f2b61a266092cd4ed7efc0))

## [0.2.1](https://github.com/atdr/github-boilerplate/compare/v0.2.0...v0.2.1) (2026-10-27)


### Bug Fixes

* **scripts:** create only the environments a repo's workflows name ([#9](https://github.com/atdr/github-boilerplate/issues/9)) ([52056cb](https://github.com/atdr/github-boilerplate/commit/52056cbb7a86a1aa72e5a6daae5a50952312eb47))
* **settings:** stop requiring PRs to be up to date with main ([#12](https://github.com/atdr/github-boilerplate/issues/12)) ([1427053](https://github.com/atdr/github-boilerplate/commit/14270535485cfce8e79b7aaf37369cc36694ee51))

## [0.2.0](https://github.com/atdr/github-boilerplate/compare/v0.1.0...v0.2.0) (2026-10-25)


### Features

* **workflows:** install uv projects from their lockfile in python-ci ([#8](https://github.com/atdr/github-boilerplate/issues/8)) ([3428401](https://github.com/atdr/github-boilerplate/commit/34284015f57b5b60b39be487266378ecdfa17720))


### Bug Fixes

* **template:** make the template coexist with Node repos' formatters ([#6](https://github.com/atdr/github-boilerplate/issues/6)) ([2102381](https://github.com/atdr/github-boilerplate/commit/2102381b81e347b518880d04dff1982d4e07d287))

## 0.1.0 (2026-10-25)


### Features

* scaffold reusable workflows, template and apply scripts ([#1](https://github.com/atdr/github-boilerplate/issues/1)) ([1797872](https://github.com/atdr/github-boilerplate/commit/17978725291ae8acd9f826275ee082514313d155))


### Bug Fixes

* **dependabot:** one PR per action bump, and group Python dev updates ([#5](https://github.com/atdr/github-boilerplate/issues/5)) ([0b776a0](https://github.com/atdr/github-boilerplate/commit/0b776a078ee34d20f4109a1af8e3f5d7752ab0a2))
* **release:** bump template pins and track repository settings ([#2](https://github.com/atdr/github-boilerplate/issues/2)) ([f4b456b](https://github.com/atdr/github-boilerplate/commit/f4b456b638f2434bc2370a5e290f38acfe722b65))
* **release:** start at 0.1.0 instead of release-please's 1.0.0 ([#4](https://github.com/atdr/github-boilerplate/issues/4)) ([cb14ee0](https://github.com/atdr/github-boilerplate/commit/cb14ee0bfc08880289149cc4c87f41aaa094a970))
