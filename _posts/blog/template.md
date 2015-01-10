---
layout: post
title: 存在感
description: This is android Project. 
category: blog
---
所有代码研究基于android4.2.2_R1 


<ul>
	<li>jekyll打开本地服务jekyll serve</li>
	<li>关于jekyll的 Address already in use - bind(2):</br>
		先采用lsof -wni tcp:4000 或者使用 ps aux |grep "jek"</br>
		再采用kill -9 PID命令
		</li>
	
</ul>

	
![Alt text]( /images/android/androidL_1.png "Optional title")


- ​http://developer.android.com/preview/api-overview.html
- ​http://developer.android.com/preview/api-overview.html
- ​http://developer.android.com/preview/api-overview.html
- ​http://developer.android.com/preview/api-overview.html	

	{% highlight java linenos %} {% endhighlight %}



### 结论

1.androd的底层实现是通过socket和共享内存的方式，这种写法也可以采用在我们自己的多进程通信上使用，值得学习
2.底层所有的event其实都是一样的，都是inputEvent，上层会根据source再分成keyEvent,MotionEvent等，用于不同的用处 
3.所有View的起点其实就是dispatchPointerEvent()，这个是分发事件的起点.


### 参考blog
[本文基于android-2.3.3_r1代码研究]: http://daemon369.github.io/android/2014/09/11/android-dispatchTouchEvent/  "本文基于android-2.3.3_r1代码研究"
[Android事件分发机制完全解析，带你从源码的角度彻底理解]: http://blog.csdn.net/guolin_blog/article/details/9153747 "Android事件分发机制完全解析，带你从源码的角度彻底理解"
[android-inputevent传递过程]:http://blog.pickbox.me/2014/05/22/android-inputevent传递过程（app端）/ "android-inputevent传递过程"


[yangming]:  
