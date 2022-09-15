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
        self.timer_dif = 0.0
        self.estimate_throughput = 0 
        self.result_bandwidth = 0 
        self.result_request = 0

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        self.send_up(msg)


    def get_bandwith_share(self):
        '''
        Calculo para obter a taxa de tranferência esperada do sistema
        '''
        return self.k*self.timer_dif*(self.w-max(0,self.avarage_bandwith - self.estimate_throughput+ self.w ))+self.avarage_bandwith

    def smoothed_bandwidth(self):
        '''
        Suavização da taxa de transferência obtida com base no algoritimo EWMA
        '''
        return self.result_bandwidth-self.alpha*self.timer_dif*(self.result_bandwidth-self.avarage_bandwith)

    def dead_zone_quant(self,new_request):
        '''
        Criação de uma zona morta para evitar perdas muito grandes no sistema
        '''

        if(new_request > self.result_request+(self.result_request*self.er)):
            return new_request
        if(new_request < self.result_request):
            return new_request
        return self.result_request

    def handle_segment_size_request(self, msg):


        #Pega os valores os tempos internos
        self.inter_request_timer = self.request_time
        self.request_time = time.perf_counter() 
        self.timer_dif = self.request_time - self.inter_request_timer
        
        

        #Fase 1 Estimativa da largura de banda 
        #base_avg_bandwith = max(0.2*self.avarage_bandwith,self.get_bandwith_share())
        base_avg_bandwith = self.get_bandwith_share()
        self.avarage_bandwith = base_avg_bandwith

        #Fase 2 Suavização para produzir a versão y[n]
        #base_bandwith = max(0.2*self.result_bandwidth,self.smoothed_bandwidth())
        base_bandwith = self.smoothed_bandwidth()
        self.result_bandwidth = base_bandwith

        # Seleciona a qualidade de video com base na largura de banda obtida
        new_request = max([ band for band in self.qi if band < base_bandwith] + [self.qi[0]])
        vd_quality = self.dead_zone_quant(new_request)
        msg.add_quality_id(vd_quality)
        self.result_request = vd_quality
        
        
        print('-------------------------------------------------------------------------------')
        print('request_time : ' + str(self.request_time))
        print('timer_dif : ' + str(self.inter_request_timer))
        print('timer_dif : ' + str(self.timer_dif))
        print('new_avarage : ' + str(base_avg_bandwith))
        print('new_bandwidth : ' + str(base_bandwith))
        print('vd_quality : ' +str(vd_quality))
        print('-------------------------------------------------------------------------------')

        
        

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
        self.k = 0.56
        self.beta = 0.2
        self.B_min = 26
        self.alpha = 0.2
        self.w = 0.3
        self.er = 0.15
        pass

    def finalization(self):
        pass