# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import subprocess
import json
import sys
import pytest

from pathlib import Path

from test_utils import REPO_ROOT


class TempGit:
    def __init__(self, cwd):
        self.cwd = cwd

    def run(self, *args):
        proc = subprocess.run(["git"] + list(args), cwd=self.cwd)
        if proc.returncode != 0:
            raise RuntimeError(f"git command failed: '{args}'")


SUCCESS_EXPECTED_OUTPUT = """
Dry run, would have merged with url=pulls/10786/merge and data={
  "commit_title": "[Hexagon] 2-d allocation cleanup (#10786)",
  "commit_message": "- Added device validity check in allocation. HexagonDeviceAPI should only be called for CPU/Hexagon types.\\n\\n- Check for \\"global.vtcm\\" scope instead of \\"vtcm\\".  The ccope of N-d allocations produced by `LowerVtcmAlloc` should be `\\"global.vtcm\\"`.  The previous check allowed unsupported scope such as `\\"local.vtcm\\"`.\\n\\n- Remove `vtcmallocs` entry after calling free.\\n\\nPreviously, the vtcm allocation map kept dangling pointers to `HexagonBuffer` objects after they had been freed.\\n\\n- Rename N-d alloc and free packed functions.  Since most of the similar device functions use snake case, renaming `*.AllocND` to `*.alloc_nd` and `*.FreeND` to `*.free_nd`.\\n\\n\\ncc someone\\n\\n\\nCo-authored-by: Adam Straw <astraw@octoml.ai>",
  "sha": "6f04bcf57d07f915a98fd91178f04d9e92a09fcd",
  "merge_method": "squash"
}
""".strip()


test_data = {
    "successful-merge": {
        "number": 10786,
        "filename": "pr10786-merges.json",
        "expected": SUCCESS_EXPECTED_OUTPUT,
        "detail": "Everything is fine so this PR will merge",
    },
    "no-request": {
        "number": 10786,
        "filename": "pr10786-nottriggered.json",
        "expected": "No merge requested, exiting",
        "detail": "A PR for which the mergebot runs but no merge is requested",
    },
    "bad-ci": {
        "number": 10786,
        "filename": "pr10786-badci.json",
        "expected": "Cannot merge, these CI jobs are not successful on",
        "detail": "A PR which failed CI and cannot merge",
    },
    "old-review": {
        "number": 10786,
        "filename": "pr10786-oldreview.json",
        "expected": "Cannot merge, did not find any approving reviews",
        "detail": "A PR with passing CI and approving reviews on an old commit so it cannot merge",
    },
    "missing-job": {
        "number": 10786,
        "filename": "pr10786-missing-job.json",
        "expected": "Cannot merge, missing expected jobs",
        "detail": "PR missing an expected CI job and cannot merge",
    },
    "invalid-author": {
        "number": 10786,
        "filename": "pr10786-invalid-author.json",
        "expected": "No merge requested, exiting",
        "detail": "Merge requester is not a committer and cannot merge",
    },
    "unauthorized-comment": {
        "number": 11244,
        "filename": "pr11244-unauthorized-comment.json",
        "expected": "No merge requested, exiting",
        "detail": "Check that a merge comment not from a CONTRIBUTOR is rejected",
    },
    "no-review": {
        "number": 11267,
        "filename": "pr11267-no-review.json",
        "expected": "Cannot merge, did not find any approving reviews from users with write access",
        "detail": "Check that a merge request without any reviews is rejected",
    },
    "changes-requested": {
        "number": 10786,
        "filename": "pr10786-changes-requested.json",
        "expected": "Cannot merge, found [this review]",
        "detail": "Check that a merge request with a 'Changes Requested' review on HEAD is rejected",
    },
    "co-authors": {
        "number": 10786,
        "filename": "pr10786-co-authors.json",
        "expected": "Co-authored-by: Some One <someone@email.com>",
        "detail": "Check that a merge request with co-authors generates the correct commit message",
    },
    "no-recomment": {
        "number": 11442,
        "filename": "pr11442-no-recomment.json",
        "expected": "No merge requested, exiting",
        "detail": "Check that comments after a failed merge don't trigger another merge",
    },
}


@pytest.mark.parametrize(
    ["number", "filename", "expected", "detail"],
    [tuple(d.values()) for d in test_data.values()],
    ids=test_data.keys(),
)
def test_mergebot(tmpdir_factory, number, filename, expected, detail):
    mergebot_script = REPO_ROOT / "tests" / "scripts" / "github_mergebot.py"
    test_json_dir = Path(__file__).resolve().parent / "sample_prs"

    git = TempGit(tmpdir_factory.mktemp("tmp_git_dir"))
    git.run("init")
    git.run("checkout", "-b", "main")
    git.run("remote", "add", "origin", "https://github.com/apache/tvm.git")
    with open(test_json_dir / filename) as f:
        test_data = json.load(f)

    proc = subprocess.run(
        [
            str(mergebot_script),
            "--pr",
            str(number),
            "--dry-run",
            "--run-url",
            "https://example.com",
            "--testing-pr-json",
            json.dumps(test_data),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        cwd=git.cwd,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Process failed:\nstdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}")

    if expected not in proc.stderr:
        raise RuntimeError(f"{proc.stderr}\ndid not contain\n{expected}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__] + sys.argv[1:]))
