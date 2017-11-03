class Temperature(object):
    def createTemperatureSensor(self):
        try:
            self.temperature = Sensors("Temp", cfg["units"]["T"], cfg["highRange"]["T"], cfg["lowRange"]["T"], "r1_tp_data.csv", 
                             0, 102, addressList, cfg["daysStored"]["days"], cfg["readsPerDay"]["reads"], "T", "")
            self.sensorList.append(self.temperature)
            self.temperature.getRead()
            self.temperature.currRead = str(self.temperature.getRead())
            if self.temperature.currRead is "NULL":
                self.emailer.warning("", addressList, "Temperature")
                self.sensorList.remove(self.temperature)
        except Exception as e:
            try:
                self.sensorList.remove(self.temperature)
            except Exception:
                pass
            t = int(time.time())
            errorstring = time.ctime(t) + ": Error: %s" % str(e)
            print(errorstring)

    # Temperature Calibration
    def temp_calibrate_loop(self):
        try:
            pg.display.update()
            myfont = pg.font.SysFont("monospace", 20)
            color = pg.Color("yellow")
            myfont.set_underline(True)
            titleScreen = myfont.render("Calibrate Temperature", 1, color)
            myfont.set_underline(False)
            myfont = pg.font.SysFont("monospace", 18)
            calibText= myfont.render("Calibrate", 1, color)
            myfont = pg.font.SysFont("monospace", 15)
            step1 = myfont.render("1. Put probe in solution", 1, color)
            step2 = myfont.render("2. Enter solution temperature", 1, color)
            step3 = myfont.render("3. Press calibrate", 1, color)
            successfulCal = myfont.render("Calibration Successful", 1, color)
            failCal = myfont.render("Calibration Failed", 1, color)
            failRetry = myfont.render("Try Again", 1, color)

            titlepos = titleScreen.get_rect()
            titlepos.centerx = self.background.get_rect().centerx + 20
            titlepos.centery = self.background.get_rect().top + 20
            calibTextpos = calibText.get_rect()
            calibTextpos.centerx = self.btmRight.centerx
            calibTextpos.centery = self.btmRight.centery
            step1pos = step1.get_rect()
            step1pos.centerx = self.topLeft.centerx + 60
            step1pos.centery = self.topLeft.centery - 30
            step2pos = step2.get_rect()
            step2pos.centerx = self.topLeft.centerx + 60
            step2pos.centery = self.topLeft.centery - 10
            step3pos = step3.get_rect()
            step3pos.centerx = self.topLeft.centerx + 60
            step3pos.centery = self.topLeft.centery + 10
            successfulCalpos = successfulCal.get_rect()
            successfulCalpos.centerx = self.background.get_rect().centerx
            successfulCalpos.centery = self.background.get_rect().centery
            failCalpos = failCal.get_rect()
            failCalpos.centerx = self.background.get_rect().centerx
            failCalpos.centery = self.background.get_rect().centery
       
            stepNum = 0
            while self.finishEvent and not self.done:
                pg.gfxdraw.rectangle(self.screen, self.backBtn, color)
                pg.draw.polygon(self.screen, color, ((30,17),(30,25),(30,17),(10,17),(15,23),(10,17),(15,11),(10,17)), 1)
                pg.gfxdraw.rectangle(self.screen, self.btmRight, color)
                self.screen.blit(titleScreen, titlepos)
                self.screen.blit(calibText, calibTextpos)
                if self.calNum != "-1111":
                    self.screen.blit(step1, step1pos)
                    self.screen.blit(step2, step2pos)
                    self.screen.blit(step3, step3pos)                                       
                pg.display.update()  

                for event in pg.event.get():
                    if(self.finishEvent == True):
                        if event.type == pg.QUIT or self.keys[pg.K_ESCAPE]:
                            self.done = True
                            self.finishEvent = False
                        elif event.type == pg.MOUSEBUTTONDOWN:
                            if self.btmRight.collidepoint(event.pos):
                                if self.temperature.i2cAddress != -1:
                                    if stepNum == 0:
                                        if self.calNum == "-1111":
                                            self.subEventNum = 5
                                            self.finishEvent = False
                                            self.numpad_event_loop("Cal Value","",1)
                                            continue
                                        elif self.calNum != "-1111":
                                            self.screen.blit(step1, step1pos)
                                            self.screen.blit(step2, step2pos)
                                            self.screen.blit(step3, step3pos)
                                            pg.display.update()
                                            stepNum = 1
                                    elif stepNum == 1:
                                        if self.tryThree('CAL,clear', self.temperature):
                                            if self.tryThree('CAL,' + str(self.calNum), self.temperature):
                                                self.screen.fill((0,0,0))
                                                self.finishEvent = False
                                                self.screen.blit(successfulCal, successfulCalpos)
                                                pg.display.update()
                                                time.sleep(1)
                                                self.calNum = "-1111"
                                                self.calibrateEventNum = 0  
                            elif self.backBtn.collidepoint(event.pos):
                                stepNum = 0
                                self.finishEvent = False
                                self.calNum = "-1111"
                                self.calibrateEventNum = 0
                        elif event.type in (pg.KEYUP, pg.KEYDOWN):
                            self.keys = pg.key.get_pressed()
                            self.finishEvent = False
                            self.calNum = "-1111"
                            self.calibrateEventNum = 0
        except:
            self.screen.fill((0,0,0))
            self.screen.blit(failCal, failCalpos)
            pg.display.update()
            time.sleep(1)
            stepNum = 0
            self.finishEvent = False
            self.calNum = "-1111"
            self.calibrateEventNum = 0




