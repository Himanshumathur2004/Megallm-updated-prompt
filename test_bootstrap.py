from workflow_common import bootstrap_env
import os

print('Before bootstrap_env:')
api_before = os.getenv('MEGALLM_API_KEY', 'NOT SET')
print(f'  MEGALLM_API_KEY={api_before}')

bootstrap_env('wf1.py')

print('\nAfter bootstrap_env:')
api_after = os.getenv('MEGALLM_API_KEY', 'NOT SET')
print(f'  MEGALLM_API_KEY={api_after}')

if api_before == api_after:
    print('\n⚠ API key was NOT changed by bootstrap_env!')
else:
    print('\n✓ API key was loaded by bootstrap_env')
