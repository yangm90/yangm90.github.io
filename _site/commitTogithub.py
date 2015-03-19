#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import commands
import os


#定义python环境版本 用于兼容3.0以上语法变更
python_ver = 2.7


#打印函数
for arg in sys.argv:   
    print arg  

#打印兼容函数
def printCompat(s1, *sn):
    printStr = None
    if len(sn) > 0:
        printStr = s1 % sn
    else:
        printStr = s1

    if python_ver < 3:
        print printStr
    else:
        print (printStr)

	

if __name__ == '__main__':
	gitAdd = "git add . ";
	os.system(gitAdd);
	gitCommit = "";
	if len(sys.argv) > 1:
		gitCommit = "git commit -m \"" + sys.argv[1] + "\" ";
	else:
		gitCommit = "git commit -m \" defalut \" ";
	printCompat("gitcommit: " + gitCommit);
	os.system(gitCommit);
	
	gitPush ="git push -u origin master";	
	os.system(gitPush);

	



