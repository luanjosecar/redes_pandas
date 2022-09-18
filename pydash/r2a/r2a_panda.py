from player.parser import *
from r2a.ir2a import IR2A
import time
import gc

class R2A_Panda(IR2A):
    def __init__(self, id):
        '''
        Inicialização de todas as tabelas que serão utilizadas no sistema
        '''
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
        '''
        Retorna os possiveis valores de requisição
        '''
        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        self.send_up(msg)


    def get_bandwith_share(self):
        '''
        Calculo para obter a taxa de tranferência esperada do sistema
        '''
        mult_pos = self.k*self.timer_dif*self.w
        mult_neg = -max(0,self.avarage_bandwith - self.estimate_throughput+ self.w )*self.k*self.timer_dif
        return mult_pos + mult_neg + self.avarage_bandwith

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
            return self.result_request*(self.er-1)
        return self.result_request

    def dead_zone_one_up_down(self,new_request):
        '''
        Criação de uma zona morta para evitar perdas muito grandes no sistema
        Código para testes retorna a variação de apenas 1 nivel de qualidade
        '''
        if(new_request == 0):
            index = 0
        else:
            index = self.qi.index(self.result_request)

        if(new_request > self.result_request+(self.result_request*self.er)):
            if(index < len(self.qi)-2):
                return self.qi[index+1]
        if(new_request < self.result_request):
            if(index > 0):
                return self.qi[index-1]
        return self.qi[index]

    def handle_segment_size_request(self, msg):
        '''
        Função para a lógica de requisições
        '''

        #Define os valores temporais
        self.timer_dif = abs(self.request_time - self.inter_request_timer)
        self.inter_request_timer = self.request_time
        self.request_time = time.perf_counter() 
        
        #Fase 1 Estimativa da largura de banda 
        base_avg_bandwith = max(self.er*self.avarage_bandwith,self.get_bandwith_share())
        self.avarage_bandwith = base_avg_bandwith

        #Fase 2 Suavização para produzir a versão y[n]
        base_bandwith = max(self.er*self.result_bandwidth,self.smoothed_bandwidth())
        self.result_bandwidth = base_bandwith


        # Seleciona a qualidade de video com base na largura de banda obtida
        #vd_quality = self.dead_zone_quant(base_bandwith)
        #new_request = max([ band for band in self.qi if band < vd_quality] + [self.qi[0]])
        new_request = self.dead_zone_one_up_down(base_bandwith)
        msg.add_quality_id(new_request)
        self.result_request = new_request
           

        self.send_down(msg)

    def handle_segment_size_response(self, msg):  
        '''
        Lida com a resposta e pausas da implementação
        '''
        self.response_time = time.perf_counter() - self.request_time
        self.estimate_throughput = msg.get_bit_length()/self.response_time

        #Pausa para o caso do buffer maior que o esperado
        if self.whiteboard.get_playback_buffer_size():
            time_for_next_request = self.beta*(self.whiteboard.get_playback_buffer_size()[-1][1] - self.B_min)
            time.sleep(max([0,time_for_next_request]))

        self.send_up(msg)


    def initialize(self):
        '''
        Inicialização do Codigo
        Define os valores Fixos
        '''
        self.k = 0.15
        self.beta = 0.7
        self.B_min = 30
        self.alpha = 0.8
        self.w = 2000
        self.er = 0.2
        pass

    def finalization(self):
        '''
        Imprimir os valores ao final do código para validação
        '''
        print('--VALUES---------------------------')
        print("K", self.k)
        print("beta", self.beta)
        print("B_min", self.B_min)
        print("alpha", self.alpha)
        print("w", self.w)
        print("er", self.er)
        print('-----------------------------------')