---
layout: post
title: Android图形的知识
description: 关于android的Canvas的知识
category: blog
---

### 关于自定义控件的基础知识
自定义控件的一个重点就是实现就是去重写他的绘制过程,也就是View.onDraw(Canvas canvas)方法。这个里面就是绘制图形的过程了，比如说一个Button，绘制按钮和按钮上的文字都是在它自己的onDraw方法中完成的。如果你想给ImageView加个蒙版，可以继承ImageView并且重写他的onDraw方法，调用完父类的onDraw之后，再自己Canvas来画一个黑色的半透明矩形，这样就可以对现有的控件进行加工了。
Canvas是什么呢？是画布，你绘制东西的时候就是绘到了这个画布上，给用户显示的东西也是这个画布上的东西。通常来说，当你调用到onDraw方法的时候对应的View已经确定了他的宽度和高度(关于View的measure和layout过程以后再详述)。那么在Canvas上，你画的范围就只有View对应的大小了。我们用代码来描述下


	{% highlight java linenos %}
	protected void onDraw(Canvas canvas) {
    super.onDraw(canvas);
    int verticalCenter    =  getHeight() / 2;
    int horizontalCenter  =  getWidth() / 2;
    int circleRadius      = 200;
    Paint paint = new Paint();
    paint.setAntiAlias(false);
    paint.setColor(Color.RED);
    canvas.drawCircle( horizontalCenter, verticalCenter-250, circleRadius, paint);

    paint.setAntiAlias(true);
    paint.setStyle(Paint.Style.STROKE);
    paint.setStrokeWidth(20);
    canvas.drawCircle( horizontalCenter, verticalCenter+250, circleRadius, paint);
}
	
	
	{% endhighlight %}


这个View的大小可以通过getHeight()和getWidth()来获得。我们准备画两个圆圈，半径都是200。我们主要用到的方法是drawCircle()方法，参数的意义分别是圆心的x，y坐标，半径和所使用的画笔Paint。

Paint是什么？是画笔的意思，Canvas是画布，Paint是画笔，画笔控制了所画东西的颜色大小字体等等。在画第一个圆的时候，我们通过Paint.setAntiAlias方法设置抗锯齿属性为false，并设置颜色为红色。

在画第二个圆的时候，我们打开了抗锯齿。将Paint的风格设为STROKE，也就是只画边框。然后设置边框宽度为20.

### 关于Canvas所涉及的到的类
android.graphics.* 包里面主要由以下一些类：
<ul>
	<li>Canvas/li>
	<li>Bitmap及其相关的类</li>
	<li>Xfermode及其子类</li>
	<li>Paint及其相关类和内部类</li>
	<li>Shader及其子类</li>
	<li>Rect，Color，Point，Path等基础类</li>
</ul>


### Canvas.drawText绘制文字为什么会偏上？
如果你经常使用Canvas的draw***方法去绘制一些图像图形，你会知道绘制的时候坐标是从Canvas左上角开始计算的，如果想要把一个图像放到某个位置，直接drawBitmap传递图片左上角的坐标就行了.

那drawText就不一样了，如果你传递进去字符串，会发现文字的位置和你指定的不一样。

卧槽为啥。Android的文档也没有仔细说，打开源码一看，又跑到native代码里去执行了。经过我奋力地Google，终于把这个问题搞清楚了。


![Alt text]( /images/android/android_drawtext.jpeg "Optional title")


对于一段文字来说，如果你想把他画到Canvas上，首先你要确定这段文字的范围，即宽度和高度，那么怎么去取这一段的高度呢，如果你在网上搜，会有很多种答案，具体应该用哪一种呢？这要看你到底需要什么样的尺寸了。

Paint.getTextBounds: 当你通过这个方法来获取尺寸的时候，你可以得到能够包裹文字的最小矩形，就是图中红色边框的那部分，你可以得到一个Rect对象，包含这个最小尺寸的几个值。坑其实就在这里：这里的Rect对象坐标并不是以左上角为准的，而是相对于左边中间靠下位置的一个点，就是图中的黄色五角星。而这里水平的Baseline指的是字符串对齐的一条线（真正的含义可以需要更深入了解字体渲染的知识了）。既然这样，r.top就是一个负值了，r.bottom会是一个小一点的正值，r.left和r.right在图中画的都很清楚。通过r.width()和r.height()来获取尺寸。

那么文字的偏移就好说了，比如说你要把文字画在Canvas的左上角，坐标是(0,0)，但是当你通过：


	{% highlight java linenos %} 
	canvas.drawText(“dangwen”,0,0,paint);
	{% endhighlight %}
来画文字的时候，发现只有文字的下半部分画出来了，因为你传递进去的参数应该是以Baseline为标准的，正确的方法是：

	{% highlight java linenos %} 
	canvas.drawText(“dangwen”,-r.left,-r.top,paint);
	
	{% endhighlight %}
Paint.getFontMetricsInt(): 当你通过这里方法来获取尺寸的时候，你获取的只是一个垂直方向上的尺寸，这里的ascent代表的是字体的上部，descent代表的是字体的下部，这里需要注意的是这和上面获得的Rect的top和bottom不太一样，他们比比ascent和descent距离稍微小一些，这些具体的高度可能和不同的字体和渲染方式有关系，这里就不深入了 #我是不懂#。

然后如果把文字写入TextView（图中蓝色部分）并且设置TextView的高度和宽度设为wrap_content，那么TextView的高度就正好是FontMetricsInt.top – FontMetricsInt.bottom, 那宽度呢？ Paint.measureText()。


	{% highlight java linenos %} {% endhighlight %}

[yangming]:  
