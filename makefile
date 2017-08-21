
### makeface (MAKEfile interFACE)
### by Ryan Bradley, distributed under copyleft please
### a crude but convenient way of making CLIs for python
### this file requires makeface.py (see the documentation there)
### this is the consensus version as of 2017.08.20

# set the shell (sh lacks source)
SHELL := /bin/bash

# CRUCIAL LINK TO THE PYTHON BACKEND!
makeface = cas/makeface.py

# script and checkfile force the execution
checkfile = .pipeline_up_to_date
protected_targets=
# pass debug flag for automatic debugging
# ! is automatica debugging deprecated
PYTHON_DEBUG = "$(shell echo $$PYTHON_DEBUG)"
# unbuffered output is best. exclude bytecode
# add the "-tt" flag here for python3 errors
python_flags = "-Butt"

# filter and evaluate
MAKEFLAGS += -s
RUN_ARGS_UNFILTER := $(wordlist 1,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
RUN_ARGS := $(filter-out $(protected_targets),$(RUN_ARGS_UNFILTER))
$(eval $(RUN_ARGS):;@:)

# valid function names from the python script
TARGETS := $(shell python $(python_flags) $(makeface) CHECKER | \
	perl -ne 'print $$1 . "\n" if /.+targets\:(.*?)\n/')
# makeface.py can specify a preliminary command to source the environment
ENV_CMD := $(shell python $(python_flags) $(makeface) CHECKER | \
	perl -ne 'print $$1 if /.+environment\:\s*(.+)/')
# make without arguments first
default: $(checkfile)
# make with arguments
$(TARGETS): $(checkfile)

# exit if target not found
controller_function = $(word 1,$(RUN_ARGS))
ifneq ($(controller_function),)
ifeq ($(filter $(controller_function),$(TARGETS)),)
    $(info [ERROR] "$(controller_function)" is not a valid make target)
    $(info [ERROR] see the makefile documentation for instructions)
    $(info [ERROR] make targets="$(TARGETS)"")
    $(error [ERROR] exiting)
endif
endif

# additions for document handling is a nearly verbatim copy of the routine above, with a specific call
#%.html: %.md
#	@/bin/echo "[STATUS] starting $<"
	
# route the make command to makeface every time
touchup:
	@touch $(checkfile)
$(checkfile): touchup
ifeq ($(ENV_CMD),)
	@env PYTHON_DEBUG=$(PYTHON_DEBUG) python $(python_flags) \
	$(makeface) ${RUN_ARGS} ${MAKEFLAGS} && \
	echo "[STATUS] exiting makeface.py" || { echo "[STATUS] fail"; exit 1; }
else
	@/bin/echo "[STATUS] environment prefix is: \""$(ENV_CMD)"\""
	( source "$(ENV_CMD)" && \
	env PYTHON_DEBUG=$(PYTHON_DEBUG) python $(python_flags) \
	$(makeface) ${RUN_ARGS} ${MAKEFLAGS} && \
	echo "[STATUS] exiting makeface.py" ) || { echo "[STATUS] fail"; exit 1; }
endif
