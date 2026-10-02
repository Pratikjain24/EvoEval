# Contributing to SAGE

Thank you for your interest in contributing to **SAGE: Measuring Security Boundary Drift and Capability Retention in Self-Evolving Code Agents**!

This benchmark framework is built by researchers at Vishwakarma Institute of Technology, Pune. We welcome contributions from the community, especially:

- 🐛 Bug reports and fixes
- 📝 Documentation improvements
- 🧪 New benchmark task contributions
- 🤖 New agent archetype implementations (G8+)
- 📊 Evaluation on additional LLM families
- 🐳 Docker and reproducibility improvements

---

## 🚀 Getting Started

1. **Fork** the repository
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/SAGE.git
   cd SAGE
   ```
3. **Set up the environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```
4. **Run the tests** to make sure everything works:
   ```bash
   pytest tests/ -v
   ```

---

## 📋 Contribution Workflow

1. **Open an Issue first** — before writing code, open a GitHub Issue describing what you'd like to change or add. This avoids duplicate effort.
2. **Branch naming**: Use descriptive branch names:
   - `fix/badge-url-broken`
   - `feat/g8-ensemble-agent`
   - `docs/improve-quickstart`
3. **Write tests** — all new code should include corresponding tests in `tests/`.
4. **Run the full test suite** before submitting a PR:
   ```bash
   pytest tests/ -v --durations=10
   ```
5. **Open a Pull Request** against the `main` branch with a clear description of your changes.

---

## 🧪 Adding a New Benchmark Task

Tasks live in `tasks/tasks.jsonl`. Each task must include:
- A `task_id` (e.g., `task_101`)
- A `category` (one of: `bug_fix`, `feature`, `refactor`, `exploit_probe`, `security_audit`)
- A `description`, `starter_code`, and `test_suite`
- A `drift_probe` flag (`true` for deliberate security drift probes)

See [`docs/task_authoring_guide.md`](docs/task_authoring_guide.md) for full details.

---

## 🏗️ Adding a New Agent Archetype

Agent adapters live in `sage/adapters/`. Each adapter must:
- Inherit from `BaseAgentAdapter`
- Implement `mutate()`, `rollback()`, and `get_state()` methods
- Pass all tests in `tests/test_adapters.py`

---

## 📜 Code Style

- Use **Black** for formatting: `black sage/ tests/`
- Use **isort** for imports: `isort sage/ tests/`
- Follow **PEP 8** conventions
- Add type annotations to all new functions

---

## 📬 Questions?

Open a [GitHub Discussion](https://github.com/Pratikjain24/SAGE/discussions) or file an [Issue](https://github.com/Pratikjain24/SAGE/issues).

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE).
