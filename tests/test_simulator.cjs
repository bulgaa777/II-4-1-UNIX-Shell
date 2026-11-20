const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const vm = require('node:vm');
const {spawnSync} = require('node:child_process');

const root = path.resolve(__dirname, '..');
const htmlPath = process.env.SIMULATOR_HTML || (fs.existsSync(path.join(root,'index.html'))?path.join(root,'index.html'):path.join(root,'Interactive/osh_HowItWorks.html'));
const html = fs.readFileSync(htmlPath, 'utf8').replace(/\r/g, '');
const script = html.split('<script>')[1].split('</script>')[0];
new vm.Script(script);
const embedded = html.split('id="oshSrc">')[1].split('</script>')[0].trim();
assert.equal(embedded, fs.readFileSync(path.join(root, 'src/osh.c'), 'utf8').replace(/\r/g, '').trim(), 'embedded C source matches src/osh.c');
const context = vm.createContext({TextEncoder});
vm.runInContext(`const B=(en,mn)=>en; const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));` +
  script.slice(script.indexOf("const CWD="), script.indexOf('let STEPS=')), context);
const model = vm.runInContext('({resetWorld,buildSteps,base:BASE_FILES,getHistory:()=>history})', context);
const plain = value => JSON.parse(JSON.stringify(value));
let count = 0;
function run(command, commit=true) {
  const run = model.buildSteps(command);
  if (commit) run.commit();
  return run;
}
function test(name, fn) {
  model.resetWorld();
  fn();
  count++;
  console.log(`PASS ${name}`);
}
const cases = [
  ['echo', 'echo hello', 'hello\n', '', 0],
  ['quoted spaces', 'echo "hi there"', 'hi there\n', '', 0],
  ['empty argument', 'echo ""', '\n', '', 0],
  ['no newline', 'echo -n hi', 'hi', '', 0],
  ['Unicode bytes', 'echo Сайн | wc -c', '9\n', '', 0],
  ['pipe', 'echo hello | wc -c', '6\n', '', 0],
  ['empty input', '', '', '', 0],
  ['whitespace', '  \t  ', '', '', 0],
  ['unknown command', 'no_such_cmd_xyz_123', '', 'no_such_cmd_xyz_123: No such file or directory\n', 127],
  ['missing input', 'cat < missing.txt', '', 'missing.txt: No such file or directory\n', 1],
  ['bad output path', 'echo hi > missing_dir/out.txt', '', 'missing_dir/out.txt: No such file or directory\n', 1],
  ['directory output', 'echo hi > docs', '', 'docs: Is a directory\n', 1],
  ['file as parent', 'echo hi > names.txt/out', '', 'names.txt/out: Not a directory\n', 1],
  ['directory input', 'cat < docs', '', 'cat: -: Is a directory\n', 1],
  ['missing filename', 'echo hi >', '', 'Missing redirection filename\n', 2],
  ['missing input filename', 'cat <', '', 'Missing redirection filename\n', 2],
  ['empty filename', 'echo hi > ""', '', 'Missing redirection filename\n', 2],
  ['operator filename', 'echo hi > "|name"', '', 'Missing redirection filename\n', 2],
  ['duplicate output', 'echo hi > a > b', '', 'Duplicate redirection\n', 2],
  ['duplicate input', 'cat < a < b', '', 'Duplicate redirection\n', 2],
  ['redirection only', '> a', '', 'Missing command\n', 2],
  ['missing right command', 'echo hi |', '', 'Missing command\n', 2],
  ['missing left command', '| wc -c', '', 'Invalid pipe\n', 2],
  ['second pipe', 'echo hi | cat | wc -c', '', 'Invalid pipe\n', 2],
  ['misplaced ampersand', 'echo & hi', '', '& must be last\n', 2],
  ['ampersand only', '&', '', 'Missing command\n', 2],
  ['unclosed quote', 'echo "hi', '', 'Unclosed quote\nInvalid command or too many arguments\n', 2],
  ['argument limit', 'echo '+Array(127).fill('x').join(' '), '', 'Invalid command or too many arguments\n', 2],
  ['token byte limit', 'echo '+'x'.repeat(4096), '', 'Invalid command or too many arguments\n', 2],
  ['empty history', '!!', '', 'No commands in history.\n', 2],
  ['false', 'false', '', '', 1],
  ['right pipeline status', 'no_such_cmd_xyz_123 | wc -c', '0\n', 'no_such_cmd_xyz_123: No such file or directory\n', 0],
  ['right pipeline failure', 'echo hello | no_such_cmd_xyz_123', '', 'no_such_cmd_xyz_123: No such file or directory\n', 127],
  ['input redirection', 'sort < names.txt', 'Anu\nBat\nBat\nTuvshin\nZaya\n', '', 0],
  ['pipe plus redirection', 'sort < names.txt | uniq > clean.txt', '', '', 0],
  ['output', 'echo sample > out.txt', '', '', 0],
  ['silent output', 'true > out.txt', '', '', 0],
  ['unknown with output', 'no_such_cmd_xyz_123 > out.txt', '', 'no_such_cmd_xyz_123: No such file or directory\n', 127],
  ['program failure with output', 'cat missing.txt > out.txt', '', 'cat: missing.txt: No such file or directory\n', 1],
  ['same file input output', 'cat < names.txt > names.txt', '', '', 0],
  ['relative path alias', 'cat < ./names.txt', 'Tuvshin\nAnu\nBat\nZaya\nBat\n', '', 0],
  ['new file in directory', 'echo hi > docs/result.txt', '', '', 0],
  ['C global output placement', 'echo hi > out.txt | wc -c', '', '', 0],
  ['C quoted operator limitation', 'echo ">"', '', 'Missing redirection filename\n', 2],
];

const compare = process.argv.includes('--compare-c');
let binary;
let compareRoot;
if(compare) {
  compareRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'osh-parity-'));
  binary = path.join(compareRoot, 'osh');
  const compile = spawnSync('cc', ['-std=c11','-Wall','-Wextra','-O2',path.join(root,'src/osh.c'),'-o',binary], {encoding:'utf8'});
  assert.equal(compile.status, 0, compile.stderr);
}
function seed(dir) {
  for(const [name,content] of Object.entries(model.base)) {
    if(content===null)fs.mkdirSync(path.join(dir,name),{recursive:true});
    else fs.writeFileSync(path.join(dir,name),content);
  }
}
function real(command, dir) {
  const output = spawnSync(binary,['-c',command],{cwd:dir,encoding:'utf8',timeout:8000,env:{...process.env,LC_ALL:'C'}});
  assert.ifError(output.error);
  return output;
}
function compareFiles(files, dir) {
  const walk = current => {
    for(const entry of fs.readdirSync(current,{withFileTypes:true})) {
      const full=path.join(current,entry.name),relative=path.relative(dir,full).split(path.sep).join('/');
      if(entry.isDirectory()){assert.equal(files[relative],null,relative);walk(full);}
      else assert.equal(files[relative],fs.readFileSync(full,'utf8'),relative);
    }
  };
  walk(dir);
  for(const name of Object.keys(files))assert.ok(fs.existsSync(path.join(dir,name)),name);
}
for(const [name,command,stdout,stderr,exitCode] of cases) {
  test(name,()=>{
    const r=run(command),result=plain(r.result);
    assert.equal(result.stdout,stdout);
    assert.equal(result.stderr,stderr);
    assert.equal(result.exitCode,exitCode);
    assert.equal(r.steps.at(-1).state.exitCode,exitCode);
    if(exitCode===2||command.trim()==='')assert.equal(r.steps.at(-1).state.procs[0].kids.length,0);
    if(compare) {
      const dir=fs.mkdtempSync(path.join(compareRoot,'case-'));seed(dir);
      const c=real(command,dir);
      assert.equal(result.stdout,c.stdout,'C stdout');
      assert.equal(result.stderr,c.stderr,'C stderr');
      assert.equal(result.exitCode,c.status,'C exit code');
      compareFiles(result.files,dir);
    }
  });
}

for(const command of ['true > out.txt','false > out.txt','no_such_cmd_xyz_123 > out.txt','cat missing.txt > out.txt']) {
  test('truncate existing: '+command,()=>{
    run('echo old-content > out.txt');
    const r=run(command);
    assert.equal(r.result.files['out.txt'],'');
    const opened=r.steps.find(s=>s.state.newFiles.includes('out.txt'));
    assert.ok(opened,'file creation/truncation step');
    assert.equal(opened.state.files['out.txt'],'','empty before exec');
    if(compare){const dir=fs.mkdtempSync(path.join(compareRoot,'truncate-'));seed(dir);real('echo old-content > out.txt',dir);const c=real(command,dir);assert.equal(c.status,r.result.exitCode);compareFiles(r.result.files,dir);}
  });
}
test('input failure leaves output untouched even if > appears first',()=>{
  run('echo old > out.txt');const r=run('cat > out.txt < missing.txt');
  assert.equal(r.result.files['out.txt'],'old\n');assert.equal(r.result.exitCode,1);
  if(compare){const dir=fs.mkdtempSync(path.join(compareRoot,'order-'));seed(dir);real('echo old > out.txt',dir);const c=real('cat > out.txt < missing.txt',dir);assert.equal(c.stderr,r.result.stderr);compareFiles(r.result.files,dir);}
});
test('parser errors have no filesystem side effects',()=>{
  const r=run('echo hi > a > b');assert.equal(r.result.files.a,undefined);assert.equal(r.result.files.b,undefined);
});
test('overwrite shorter text removes suffix',()=>{run('echo very-long-text > out.txt');const r=run('echo x > out.txt');assert.equal(r.result.files['out.txt'],'x\n');});
test('read previously redirected output',()=>{run('echo sample > out.txt');assert.equal(run('cat < out.txt').result.stdout,'sample\n');});
test('history replay',()=>{run('echo first');assert.equal(run('!!').result.stdout,'echo first\nfirst\n');assert.equal(model.getHistory(),'echo first');});
test('blank preserves history',()=>{run('echo first');run('');assert.equal(run('!!').result.stdout,'echo first\nfirst\n');});
test('C whitespace history behavior',()=>{run('echo first');run('   ');assert.equal(model.getHistory(),'   ');assert.equal(run('!!').result.stdout,'   \n');});
test('blank preserves previous interactive result',()=>{run('false');assert.equal(run('').result.exitCode,1);assert.equal(run('   ').result.exitCode,0);});
test('failed command is replayable',()=>{run('no_such_cmd_xyz_123');assert.equal(run('!!').result.exitCode,127);});
test('background return code is launch status',()=>{
  const r=run('no_such_cmd_xyz_123 &');assert.equal(r.result.exitCode,0);assert.match(r.result.stdout,/\[background\] PID \d+\n/);assert.equal(r.steps.at(-1).state.procs[0].kids[0].exit,127);
});
test('background timeline shows prompt before reaping',()=>{
  const r=run('sleep 3 &');const prompt=r.steps.findIndex(s=>s.state.bgPrompt);
  const zombie=r.steps.findIndex(s=>s.state.procs[0].kids.some(c=>c.state==='zombie'));
  const reaped=r.steps.findIndex(s=>s.state.procs[0].kids.some(c=>c.state==='reaped'));
  assert.ok(prompt>=0&&prompt<zombie&&zombie<reaped);
});
test('cd fails and pwd remains unchanged',()=>{const before=run('pwd').result.stdout;assert.equal(run('cd /tmp').result.exitCode,127);assert.equal(run('pwd').result.stdout,before);});
test('step snapshots keep pre-truncation contents',()=>{run('echo old > out.txt');const r=run('true > out.txt');assert.equal(r.steps[0].state.files['out.txt'],'old\n');assert.equal(r.result.files['out.txt'],'');});
test('reset restores files, history, PIDs and result',()=>{run('echo hi > out.txt');run('false');model.resetWorld();assert.equal(run('!!').result.exitCode,2);model.resetWorld();const r=run('echo hi');assert.equal(r.result.files['out.txt'],undefined);assert.equal(r.steps.at(-1).state.procs[0].kids[0].pid,4101);});
test('bilingual concepts and defense explanations',()=>{
  assert.ok(html.includes('Shell-ийн гол дуудлагууд ба zombie төлөв'));
  for(const text of ['Are all six cards system calls?','Why must cd run in the parent shell?','Why can an unknown command empty an output file?'])assert.ok(html.includes(text));
});
for(const commands of [
  ['echo first','!!'],
  ['echo first','','!!'],
  ['echo first','   ','!!'],
  ['false',''],
  ['no_such_cmd_xyz_123','!!'],
  ['echo old > out.txt','no_such_cmd_xyz_123 > out.txt','cat < out.txt'],
  ['echo old > out.txt','cat > out.txt < missing.txt','cat < out.txt'],
]) {
  test('interactive session: '+JSON.stringify(commands),()=>{
    const results=commands.map(command=>run(command).result);
    if(compare){
      const dir=fs.mkdtempSync(path.join(compareRoot,'session-'));seed(dir);
      const c=spawnSync(binary,[],{cwd:dir,input:commands.join('\n')+'\nexit\n',encoding:'utf8',timeout:8000,env:{...process.env,LC_ALL:'C'}});
      assert.ifError(c.error);
      assert.equal(results.map(r=>r.stdout).join(''),c.stdout.replaceAll('osh> ',''),'session stdout');
      assert.equal(results.map(r=>r.stderr).join(''),c.stderr,'session stderr');
      assert.equal(results.at(-1).exitCode,c.status,'session status');
      compareFiles(results.at(-1).files,dir);
    }else assert.equal(results.length,commands.length);
  });
}
if(compare)fs.rmSync(compareRoot,{recursive:true,force:true}); // Зөвхөн тестийн үүсгэсэн түр хавтас.
console.log(`PASS: ${count} simulator checks${compare?' (C parity enabled)':''}`);
