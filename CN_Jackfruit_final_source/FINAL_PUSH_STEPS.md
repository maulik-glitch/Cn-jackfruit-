# Apply the final CN Jackfruit update to your GitHub clone

1. Download the final source ZIP and extract it directly into the root of your
   cloned `Cn-jackfruit-` repository. Allow files to be overwritten when asked.
   The archive is arranged to place the project under
   `cn-jackfruit/cn-jackfruit/`, matching the current repository layout.

2. Open PowerShell or the VS Code terminal at the repository root and remove
   the generated files that were already committed in the previous version:

   ```powershell
   git rm -f cn-jackfruit/cn-jackfruit/main_code/__pycache__/exam_data.cpython-315.pyc
   git rm -f cn-jackfruit/cn-jackfruit/main_code/logs/server.log
   git rm -f cn-jackfruit/cn-jackfruit/main_code/logs/server_metrics.csv
   git rm -f cn-jackfruit/cn-jackfruit/main_code/results/load_test_clients_latest.csv
   git rm -f cn-jackfruit/cn-jackfruit/main_code/results/load_test_latest.json
   ```

   If Git reports that any one of those paths does not exist, continue with the
   remaining paths.

3. Review and commit the final update:

   ```powershell
   git status
   git add -A
   git commit -m "Finalize CN Jackfruit socket and SDN deliverables"
   git push origin main
   ```

4. Refresh the GitHub repository page and confirm the latest commit appears on
   `main`. The source ZIP itself is not a substitute for the Git push.

The SDN source is included, but live OpenFlow evidence still needs to be run in
an Ubuntu/Mininet environment as documented in `sdn/README.md`.
