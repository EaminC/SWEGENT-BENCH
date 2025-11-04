我现在想要build一个工具 这个工具可能有一点点复杂 整体而言他的目的是为了给一些agent有关的repo创建测试用例并验证 所以我会说的仔细一点
这个工具我希望：
1.写在/home/cc/SWEGENT-BENCH/src/test-gen
2.他的前提假设是 我现在的路径在一个repo(例子：/home/cc/SWEGENT-BENCH/codex)里；我有一个为这个repo弄好的dockerfile(例子：/home/cc/SWEGENT-BENCH/codex/claude.dockerfile)；我有一个这个repo的issue json（例子：/home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json）

现在我想要做的事情是
1.让ai读取当前repo，并且读取json中的内容（包含issue信息 pr信息 patch信息 这里需要你写一个程序展开这个json），让ai干事情的脚本写在/home/cc/SWEGENT-BENCH/src/test-gen/claude/run_claude.py 这里已经有一些内容但是他是配置环境的 把提示词改成配置环境的
2.让ai写一个测试脚本，基于unitest，但是由于这是一个agent有关的repo 有些bug可能和里面一些远程api交互无关 所以我想要mock掉，所以写测试的时候可以参考/home/cc/SWEGENT-BENCH/src/repo-build/env_pool.json
/home/cc/SWEGENT-BENCH/src/repo-build/mock_interface.md
/home/cc/SWEGENT-BENCH/src/repo-build/mock_interface.md里面的一些指引
3.最后形成以后我希望ai能够运行这个docker 然后在原本有bug版本运行这个测试 然后加patch之后在无bug版本运行测试 最佳结果是之前有bug 之后无bug
