from player.parser import *
from r2a.ir2a import IR2A
import time
import gc

class R2A_Panda(IR2A):
    def __init__(self, id):
        IR2A.__init__(self, id)
        self.qi = []

        #Variáveis de utilização do algoritimo PANDA
        #Tabela 1 Notações do artigo 
        self.k = 0 #Probing convergence rate
        self.w = 0 # Probing additive increase bitrate
        self.alpha = 0 # Smoothing convergence rate
        self.beta = 0 # Client buffer convergence rate
        self.er = 0 # Multiplicative safety margin --- Verificar a utilização
        self.B_min = 0 # Minimum client buffer duration
        
        self.request_time = 0
        self.inter_request_timer = 0
        self.avarage_bandwith = 0
        self.estimate_bandwith = 0
        self.timer_dif = 0
        self.estimate_throughput = 0 
        self.smoothed_bandwidth = 0 

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        self.send_up(msg)


    def get_bandwith_share(self):
        return self.k*self.timer_dif*(self.w-max(0,self.avarage_bandwith - self.estimate_throughput+ self.w ))+self.avarage_bandwith

    def smoothed_bandwidth(self):
        #Implementação suavisador EWMA
        return self.smoothed_bandwidth-self.alpha*self.timer_dif*(self.smoothed_bandwidth-base_avg_bandwith)

    def handle_segment_size_request(self, msg):


        #Pega os valores os tempos internos
        self.timer_dif = abs(self.request_time - self.inter_request_timer)
        self.inter_request_timer = self.request_time
        self.request_time = time.perf_counter() 
        

        #Fase 1 Estimativa da largura de banda 
        base_avg_bandwith = max(0.2*self.avarage_bandwith,self.get_bandwith_share())

        #Fase 2 Suavização para produzir a versão y[n]
        base_bandwith = max(0.2*self.smoothed_bandwidth,smoothed_bandwidth())

        # Seleciona a qualidade de video com base na largura de banda obtida
        vd_quality = max([ band for band in self.qi if band < new_bandwidth] + [self.qi[0]])
        msg.add_quality_id(vd_quality)
        
        
        print('-------------------------------------------------------------------------------')
        print('request_time : ' + str(self.request_time))
        print('timer_dif : ' + str(self.timer_dif))
        print('new_avarage : ' + str(base_avg_bandwith))
        print('avarage_bandwith : ' + str(self.avarage_bandwith))
        print('new_bandwidth : ' + str(base_bandwith))
        print('bandwidth_shares : ' + str(self.smoothed_bandwidth))
        print('-------------------------------------------------------------------------------')

        #Valores são alocados novamente
        self.avarage_bandwith = base_avg_bandwith
        self.smoothed_bandwidth = base_bandwith

        self.send_down(msg)

    def handle_segment_size_response(self, msg):  
        self.response_time = time.perf_counter() - self.request_time
        self.estimate_throughput = msg.get_bit_length()/self.response_time

        print("ESTIMATED TH: " + str(self.estimate_throughput))

    
        if self.whiteboard.get_playback_buffer_size():
            time_for_next_request = self.beta*(self.whiteboard.get_playback_buffer_size()[-1][1] - self.B_min)
            time.sleep(max([0,time_for_next_request]))

        self.send_up(msg)


    def initialize(self):
        #Rodar mais vezes com base nos algoritimos citados lá
        self.k = 0.5
        self.beta = 0.5
        self.B_min = 40
        self.alpha = 0.5
        self.w = 200000
        pass

    def finalization(self):
        pass