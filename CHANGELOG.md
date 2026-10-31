# Changelog

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
