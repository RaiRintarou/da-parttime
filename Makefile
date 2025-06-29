export PWD=`pwd`
export PYTHONPATH=$PYTHONPATH:$(pwd)
export PYTHON=poetry run python
export PYSEN=poetry run pysen
export NEWCOMER = tes
export DEPARTMENT = department

run:
	$(PYTHON) run.py --newcomer $(NEWCOMER) --department $(DEPARTMENT)

streamlit:
	poetry run streamlit run streamlit_shift_matching_demo.py
lint:
	$(PYSEN) run lint

format:
	$(PYSEN) run format

prof:
	$(PYTHON) -m cProfile -o profile_output.pstats run.py --case_name $(CASE_NAME)

snakeviz:
	poetry run snakeviz profile_output.pstats