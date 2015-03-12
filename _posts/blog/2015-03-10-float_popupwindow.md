---
layout: post
title: Activity 上的悬浮窗
description: 采用popupWindow做悬浮窗 
category: blog
---
所有代码研究基于android4.2.2_R1 

## 研究原因
    做悬浮窗最常见的方式是采用windowManager这个类来实现,调用这个类的addView方法去添加一个悬浮窗，用updateViewLayout方法用于新悬浮窗的参数,removeView用于移除悬浮窗。但是用这个方法去实现悬浮窗有个问题,需要添加权限<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />。这个是dangerous权限。我们不需要在桌面上显示，只是在程序内部显示，所以不需要这么高的权限，最终选择使用popupWindow.

### 关于popupwindow去做悬浮窗
    
习惯性的用google，搜索了相关资料： [Android: How to drag(move) PopupWindow?](http://stackoverflow.com/questions/9035678/android-how-to-dragmove-popupwindow)
但是发现这个答案其实一点都不完美。实现的效果很渣渣。所以想这篇Blog去讲讲遇到的问题和解决方法。
主要遇到的问题

- mPopup.showAtLocation(cv, Gravity.RIGHT, mCurrentX, mCurrentY)改变Gravity属性会对popupWindow的位置计算有很大影响.
- 每次重新拖动的时候会从原点重新计算。

### popupWindow移动的核心实现

复写onTouchEvent事件，在移动的过程中不停的用popupWindow.update()方法就可以。

```java
	@Override
            public boolean onTouch(View v, MotionEvent event) {
                int action = event.getAction();
                switch (action) {
                case MotionEvent.ACTION_DOWN:
                    main_lastX = (int) event.getRawX();
                    main_lastY = (int) event.getRawY();
                    break;
                case MotionEvent.ACTION_UP:
                    main_mScreenX = main_dx;
                    main_mScreenY = main_dy;
                    break;
                case MotionEvent.ACTION_MOVE:
                    main_dx = (int) event.getRawX() - main_lastX + main_mScreenX;
                    main_dy =  main_lastY - (int)event.getRawY() + main_mScreenY;
                    pop_main.update( main_dx,main_dy, -1, -1);
                    break;
                }
                return true;
            }
	
```

### 曾近遇到的问题

- MotionEvent.getX() 和 getRawX()的区别：
getX()是触摸后获得相对于自身控件的的X坐标,最大值不会超过自身View的宽度。
getRawX() 是触摸后获得相对于屏幕位置的X坐标。
- 关于popupwindow.update(x,y,width,height,force)这里的X,Y要传的就是屏幕坐标。


[yangming]:  
