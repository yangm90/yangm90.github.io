---
layout: post
title: git多个SSh Key
description: 关于git如何关联共有库和私有库
category: blog
---
所有代码研究基于android4.2.2_R1 


## 问题
  因为最近项目会采用git去管理项目，但是我平时电脑也会用git去commit我自己的项目,所以会碰到多个密钥管理的问题。

###生成公钥的方式

	{% highlight shell linenos %} 
	$ ssh-keygen -t rsa -C "your_email@example.com"
# Creates a new ssh key, using the provided email as a label
 Generating public/private rsa key pair.
 Enter file in which to save the key (/Users/you/.ssh/id_rsa): [Press enter]
	{% endhighlight %}

这里会提示输入密码,如果你需要每次输入密码,可以输入.

### 将Key加入到ssh中
假设你生成的两个key是这样的:

	{% highlight shell linenos %} 
	~/.ssh/id_rsa_activehacker
	~/.ssh/id_rsa_jexchan
	{% endhighlight %}
将这两个Key加入到ssh中

	{% highlight java linenos %} 
	$ ssh-add ~/.ssh/id_rsa_activehacker
	$ ssh-add ~/.ssh/id_rsa_jexchan
	{% endhighlight %}

然后检测下保存的key

	{% highlight shell linenos %} 
	$ ssh-add -l
	{% endhighlight %}

### 编辑ssh config文档	
配置何时使用哪个key


	{% highlight shell linenos %} 
$ cd ~/.ssh/
$ touch config
$ subl -a config

	{% endhighlight %}

### Clone 你的项目,配置你自己项目的config

例如clone自己的项目: git@github.com:activehacker/gfs.git gfs_jexchan
进入gfs_jexchan，执行

	{% highlight shell linenos %} 
$ git config user.name "jexchan"
$ git config user.email "jexchan@gmail.com" 

	{% endhighlight %}
或者使用全局的config

	{% highlight shell linenos %} 
$ git config --global user.name "jexchan" 
$ git config --global user.email "jexchan@gmail.com"
	{% endhighlight %}

然后就可以正常使用了.


[yangming]:  
