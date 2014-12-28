---
layout: post
title: 关于java String的匹配问题
description: 关于String的一些想法
category: blog
---
### 遇到的问题

这次在调程序性能的时候发现有多处的String匹配，加上各种云端开关，想到之前字符串匹配用到的KMP算法，所以打算采用KMP算法：


	{% highlight java linenos %}
	public class KMP {
    public int kmpMatch(String s, String p){
        int[] next = new int[s.length()];
        int i,j;
        i=0;
        j=0;
        getNext(p,next);
        while(i<s.length()){
            if(j==-1||s.charAt(i)==p.charAt(j)){
                i++;
                j++;
            }else{
                j=next[j]; // eliminate Trace Back
            }
            if(j==p.length()){
                return i-p.length();
            }
        }
        return -1;
    }

    private void getNext(String p, int[] next){
        int j,k;
        next[0]=-1;
        j=0;
        k=-1;
        while(j<p.length()-1){
            if(k==-1 || p.charAt(j)==p.charAt(k)){
                j++;
                k++;
                next[j]=k;
            }else{
                k=next[k];
            }
        }
    }
}
	{% endhighlight %}
	
但是发现，性能竟然降下去了。

### 关于java的字符串匹配的问题
	我们之前的代码采用的jdk的**contains api**
	源码如下：
	![Alt text]( /images/android/2014_java_indexof.png "Optional title")

	发现牛逼的jre源码竟然采用了最朴实的算法,我们知道KMP的时间复杂度是非常好的为o(n)
为何源码采用朴素算法,不采用KMP？在stackOverFlow上找到了一些蛛丝马迹:
	KMP算法具有更好的性能，但实际上需要一点点的前面计算（产生的偏移量表）。IT也需要一个初始的内存分配，这也可能影响性能。
	而且使用String的**charAt **会对性能的造成损耗，这个需要注意！！！
	
此外，测试了了String的几个查找subString的API：

1. string.contains()
2. string.indexOf()
3. regular expression. it is something like string.matches("ja"))

性能 string.indexOf() > string.contains() > string.matches("ja"))

	
[yangming]:  
