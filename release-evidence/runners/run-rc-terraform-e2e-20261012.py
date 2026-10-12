#!/usr/bin/env python3
"""Run the committed Terraform assertions using the exact unsigned RC binary."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

root = Path(sys.argv[1]).resolve()
binary = Path(sys.argv[2]).resolve()
result_file = Path(sys.argv[3])
source = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
assert not subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=no']).strip()
sys.path.insert(0, str(root / 'tests/e2e'))
import test_e2e_terraform as module
module.TERRAFORM_IMAGE = 'hashicorp/terraform:1.14.9@sha256:1d10ec4073f4ddbdf34a28540a3b9250852ab500cb1c53f68c8bd17d82f474d8'
module.PROVIDER_SOURCE = 'registry.terraform.io/mischapogr/platformipam'
os.environ['IPAM_E2E_KEEP_WORKSPACE'] = '1'

def prepare(cls):
    if cls.workspace.exists():
        shutil.rmtree(cls.workspace)
    plugins = cls.workspace / 'plugins'
    plugins.mkdir(parents=True)
    config = cls.workspace / 'config'
    config.mkdir()
    target = plugins / 'terraform-provider-platformipam'
    shutil.copyfile(binary, target)
    target.chmod(0o755)
    (cls.workspace / 'terraform.rc').write_text(
        'provider_installation {\n  dev_overrides {\n    "' + module.PROVIDER_SOURCE + '" = "/plugins"\n  }\n  direct {}\n}\n')
    (config / 'main.tf').write_text(module.MAIN_TF % {'source':module.PROVIDER_SOURCE})

module.TerraformE2ETest._prepare_workspace = classmethod(prepare)
class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = []
    def addSuccess(self, test):
        self.passed.append(test.id())
        super().addSuccess(test)

suite = unittest.defaultTestLoader.loadTestsFromTestCase(module.TerraformE2ETest)
result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
record = {'source_commit':source,'provider_version':'0.1.0-rc.1','provider_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
          'provider_address':module.PROVIDER_SOURCE,'terraform_image':module.TERRAFORM_IMAGE,'tests_run':result.testsRun,
          'passed_tests':result.passed,'skips':len(result.skipped),'errors':len(result.errors),'failures':len(result.failures),
          'evidence_boundary':'simulation','aws_readiness_notice':'AWS API/AWS integration is not yet ready'}
record['status'] = 'PASSED' if result.wasSuccessful() and result.testsRun == 2 and not result.skipped else 'FAILED'
result_file.write_text(json.dumps(record, indent=2, sort_keys=True)+'\n')
print(json.dumps(record, sort_keys=True))
sys.exit(0 if record['status']=='PASSED' else 1)
