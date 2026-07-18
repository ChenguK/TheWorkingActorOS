const [majorText] = process.versions.node.split(".");
const major = Number(majorText);
const userAgent = process.env.npm_config_user_agent ?? "";
const npmMatch = userAgent.match(/npm\/(\d+)/);
const npmMajor = npmMatch ? Number(npmMatch[1]) : null;

if (!Number.isFinite(major) || major < 20 || major >= 23) {
  console.error(
    [
      "The Working Actor OS frontend requires Node.js >=20 <23.",
      `Current Node.js: ${process.versions.node}`,
      "Run: nvm install && nvm use"
    ].join("\n")
  );
  process.exit(1);
}

if (npmMajor !== null && npmMajor < 10) {
  console.error(
    [
      "The Working Actor OS frontend requires npm >=10.",
      `Current npm: ${npmMajor}`,
      "Run: nvm install && nvm use"
    ].join("\n")
  );
  process.exit(1);
}
