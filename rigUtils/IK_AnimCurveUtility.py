##!/usr/bin/env python
# Irakli Kublashvili 2018
from pymel.core import*
from pymel.core import*
import random
from functools import partial


class IK_AnimCurveUtilitieCLass(object):
    
    def __init__(self): 
        super(IK_AnimCurveUtilitieCLass, self).__init__()
        
        self.IK_animCurveUtility_UI()
        
    def IK_animCurveUtilitie(self, whichButton=None,  *args):
        
        

        reverse = False
        move = False
        scale = False
        
        if whichButton == 'reverse':
            reverse = True
        if whichButton == 'move':
            move = True
        if whichButton == 'scale':
            scale = True
        
        characters = selected(l=True)

        # Get/Generate value
        minVal = floatField(self.minVal_ff, query=True, value=True)
        maxVal = floatField(self.maxVal_ff, q=True, value=True)
        moveVal = floatField(self.moveBy, q=True, value=True)
        scalePivotVal = floatField(self.scalePivot, query=True, value=True)
        scaleVal = floatField(self.scaleBy, query=True, value=True)
        value = []
        for x in range(len(characters)):
          if not reverse and not move and not scale:
            value.append(random.randint(minVal ,maxVal))
          elif move:
              value.append(moveVal)
              
        for index, character in enumerate(characters):
            # Get child curves
            shapes = ls(character, dag=True, type='nurbsCurve',l=True )
            transforms = [x.getParent() for x in shapes]

            
            # Get anim curves from controlers
            animCurves = []
            for t in transforms:
                for attr in t.listAttr(k=True, v=True):
                    if attr.inputs():
                        # Check if the anim curve is not driven
                        if not nodeType(attr.inputs()[0]) == 'animCurveUU':
                            animCurves.append(attr.inputs()[0])
            # Move curves
            
            for animCurve in animCurves:
            # Get current times and add/substract user value
                currentTimes = keyframe(animCurve, query=True, timeChange=True)
                if not reverse and not scale:
                    newTimes = list([x+(value[index]) for x in currentTimes])
      
                #print newTimes
                #Move anim curves
                if reverse:
                    scaleKey(animCurve, time=(currentTimes[0], currentTimes[-1]), newStartTime=currentTimes[-1], newEndTime=currentTimes[0])    
                elif move:
                    scaleKey(animCurve, time=(currentTimes[0], currentTimes[-1]), newStartTime=newTimes[0], newEndTime=newTimes[-1])
                elif scale:
                    scaleKey(animCurve, time=(currentTimes[0], currentTimes[-1]), timeScale=scaleVal, timePivot=scalePivotVal)
                else:
                    scaleKey(animCurve, time=(currentTimes[0], currentTimes[-1]), newStartTime=newTimes[0], newEndTime=newTimes[-1])
    
    
    def IK_animCurveUtility_UI(self, *args):        
        if(cmds.window('IK_main_AnimUtiliWindow',q=1,ex=1)):
            cmds.deleteUI('IK_main_AnimUtiliWindow')
            
        cmds.window('IK_main_AnimUtiliWindow',s=0,t='IK Animation Utilities v2.0',h=145,mb=1)
        cmds.formLayout('mainForm_ly',h=145)
        cmds.columnLayout('mainColumn_ly')
        cmds.rowLayout('randomize_ly',nc=7)
        cmds.button('randomize_btn',l='Randomize', command=partial(self.IK_animCurveUtilitie, 'randomize'))
        cmds.separator('randSeparator',st='single',w=5,h=20)
        cmds.text('minVal_txt',l='Min:')
        self.minVal_ff = cmds.floatField('minVal_ff')
        cmds.text('r_dummy_txt',l=' ')
        cmds.text('maxVal_txt',l='Max:')
        self.maxVal_ff = cmds.floatField('maxVal_ff')
        cmds.separator('mainSeparator_01',p='mainColumn_ly',w=290,h=12,hr=1)
        cmds.rowLayout('scale_ly',p='mainColumn_ly',nc=7)
        cmds.button('retime_btn',w=63,l='Retime', command=partial(self.IK_animCurveUtilitie, 'scale'))
        cmds.separator('scaleSeparator',st='single',h=20,w=5)
        cmds.text('scale_txt',l='Scale:')
        self.scaleBy =cmds.floatField('scale_ff')
        cmds.text('s_dummy_txt',l=' ')
        cmds.text('pivot_txt',l='Pivot:')
        self.scalePivot = cmds.floatField('pivot_ff')
        cmds.separator('mainSeparator_02',p='mainColumn_ly',h=12,w=290,hr=1)
        cmds.rowLayout('offset_ly',p='mainColumn_ly',nc=4)
        cmds.button('offset_btn',w=65,l='Offset', command=partial(self.IK_animCurveUtilitie, 'move'))
        cmds.separator('offsetSeparator',st='single',w=5,h=20)
        cmds.text('move_txt',l='Move:')
        self.moveBy = cmds.floatField('move_ff')
        cmds.separator('mainSeparator_03',p='mainColumn_ly',w=290,h=12,hr=1)
        cmds.rowLayout('buttons_ly',p='mainColumn_ly',nc=7)
        cmds.button('reverse_btn',w=90,l='Reverse', command=partial(self.IK_animCurveUtilitie, 'reverse'))
        cmds.separator('reverseSeparator',st='single',w=5,h=20)
        cmds.button('copy_btn',w=90,l='Copy', command=lambda x:cmds.copyKey())
        cmds.separator('copySeparator',st='single',h=20,w=5)
        cmds.button('paste_btn',w=90,l='Paste', command=lambda x:cmds.pasteKey())
        cmds.showWindow('IK_main_AnimUtiliWindow')


IK_AnimCurveUtilitieCLass()