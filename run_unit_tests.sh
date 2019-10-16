#!/usr/bin/env bash
set -ex

CUR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_COLOR="\033[1;34m\n\n"
ERR_COLOR="\033[1;31m\n\n"
NO_COLOR="\n\033[0m"

if [ ! -d "${CUR_DIR}/../../server/" ]; then
  echo -e "${ERR_COLOR}!Could not find server repo!${NO_COLOR}"
  exit 1
fi

if [ -z "$GAE" ]; then
  GAE="/usr/local/google_appengine/"
fi

if [ ! -d "$GAE" ]; then
  echo -e "${ERR_COLOR}!Could not find google_appengine folder!${NO_COLOR}"
  exit 1
fi

echo -e "${LOG_COLOR}* Running unit-tests ${NO_COLOR}"
pushd ${CUR_DIR}/../../server/
PYTHONPATH=.:libs:$GAE:$GAE/lib/jinja2-2.6/:$GAE/lib/webob_0_9/:$GAE/lib/webapp2-2.5.2/:$GAE/lib/jinja2-2.6/ python2 ${CUR_DIR}/tests/__init__.py
popd
