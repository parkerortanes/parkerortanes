# Setup (about 5 minutes)

1. **Create your profile repo.** On GitHub, make a new **public** repo named exactly your username (e.g. `parkerortanes/parkerortanes`). GitHub shows its README on your profile page.
2. **Upload these files** to it, keeping the folder structure (`.github/workflows/update-readme.yml` must stay in that folder).
3. **Fill in the TODOs** in `profile.yml`: your GitHub username, LinkedIn link, firm name, and internship dates.
4. **Allow the bot to commit:** repo → Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save.
5. **Run it once:** Actions tab → "Update README" → **Run workflow**.

## How it stays updated

| What changes | How it gets into your README |
|---|---|
| Your repos and commits | Pulled from GitHub every morning automatically |
| "Right now" status (incoming, current, past) | Calculated from the dates in `profile.yml` every day |
| A new job, offer, award, leadership role | Add a line under `news:` (and `experience:` if it's a role) in `profile.yml` and commit. It rebuilds within a minute |

Anything you write in `README.md` **outside** the `<!-- START -->`/`<!-- END -->` markers is left alone, so you can add your own sections.

Remember: everything in `profile.yml` is public.
